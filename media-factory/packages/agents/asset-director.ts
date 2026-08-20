import { existsSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import {
  AssetPlanSchema,
  type Asset,
  type AssetPlan,
  type Brand,
  type Scene,
  type Storyboard,
} from '../core/types.ts';

/**
 * The asset director is the boundary between "we need media" and "a provider
 * actually made media". Planning stays deterministic and offline; generation
 * only happens when a provider is configured and authenticated.
 *
 * Important invariants:
 * - no API key => no network call and no fake success
 * - provider failure => the original placeholder survives with a warning
 * - text graphics remain native Remotion work, not paid provider calls
 * - captured/non-synthetic assets are never replaced by generated media
 */

export type MediaKind = 'image' | 'video';

export interface GeneratedMedia {
  uri: string;
  mediaKind: MediaKind;
  provider: string;
  note?: string;
}

export interface AssetGenerationContext {
  brand: Brand;
  storyboard: Storyboard;
  scene: Scene;
  asset: Asset;
  isHook: boolean;
  config: BrandProviderConfig;
}

export interface AssetGenerationProvider {
  id: string;
  canHandle(context: AssetGenerationContext): boolean;
  generate(context: AssetGenerationContext): Promise<GeneratedMedia>;
}

export interface BrandProviderConfig {
  heygen?: {
    enabled?: boolean;
    avatarId?: string;
    voiceId?: string;
    resolution?: '720p' | '1080p' | '4k';
    talkingHeadSceneNumbers?: number[];
  };
  runway?: {
    enabled?: boolean;
    model?: string;
    ratio?: string;
  };
}

export interface DirectAssetsOptions {
  brand: Brand;
  storyboard: Storyboard;
  assetPlan: AssetPlan;
  brandsDirectory?: string;
  /** Tests or alternate runtimes can inject providers without touching env. */
  providers?: AssetGenerationProvider[];
}

export interface DirectedAssetsResult {
  assetPlan: AssetPlan;
  warnings: string[];
}

const DEFAULT_RUNWAY_MODEL = 'gemini_image3_pro';
const DEFAULT_RUNWAY_RATIO = '1080:1920';
const RUNWAY_API_VERSION = '2024-11-06';
const DEFAULT_POLL_MS = 2_500;
const DEFAULT_MAX_POLLS = 72;

export async function directAssets(options: DirectAssetsOptions): Promise<DirectedAssetsResult> {
  const config = loadProviderConfig(options.brand.id, options.brandsDirectory);
  const providers = options.providers ?? defaultProviders(config);
  const warnings: string[] = [];
  const firstSceneNumber = options.storyboard.scenes[0]?.sceneNumber ?? 1;

  const directed: Asset[] = [];

  for (const asset of options.assetPlan.assets) {
    const scene = options.storyboard.scenes.find((candidate) => candidate.sceneNumber === asset.sceneNumber);
    if (!scene) {
      directed.push(asset);
      warnings.push(`asset director: scene ${asset.sceneNumber} was not found; kept ${asset.id} unchanged.`);
      continue;
    }

    // Remotion owns typography, badges and CTA cards. Calling a paid media
    // provider for these would add cost and usually reduce text fidelity.
    if (asset.type === 'text_graphic') {
      directed.push({
        ...asset,
        status: 'ready',
        sourceNote: 'provider:remotion; media:graphic; rendered natively by the final compositor',
      });
      continue;
    }

    // Mixed-mode real footage is an operator-owned source. Never overwrite it
    // with synthetic media just because a provider happens to be configured.
    if (!asset.synthetic) {
      directed.push(asset);
      continue;
    }

    const context: AssetGenerationContext = {
      brand: options.brand,
      storyboard: options.storyboard,
      scene,
      asset,
      isHook: scene.sceneNumber === firstSceneNumber,
      config,
    };

    const ordered = rankProviders(context, providers);
    if (ordered.length === 0) {
      directed.push(asset);
      continue;
    }

    let generated: GeneratedMedia | null = null;
    const failures: string[] = [];

    for (const provider of ordered) {
      try {
        generated = await provider.generate(context);
        if (generated.uri) break;
      } catch (error) {
        failures.push(`${provider.id}: ${(error as Error).message}`);
      }
    }

    if (!generated) {
      directed.push(asset);
      if (failures.length > 0) {
        warnings.push(
          `asset director: scene ${scene.sceneNumber} stayed placeholder after provider failure(s): ${failures.join(' | ')}`,
        );
      }
      continue;
    }

    directed.push({
      ...asset,
      status: 'ready',
      uri: generated.uri,
      sourceNote: [
        `provider:${generated.provider}`,
        `media:${generated.mediaKind}`,
        generated.note,
      ].filter(Boolean).join('; '),
    });
  }

  return {
    assetPlan: AssetPlanSchema.parse({
      ...options.assetPlan,
      assets: directed,
      // Provider generation is still synthetic unless the original plan said
      // otherwise. A pretty render must never become evidence of product use.
      allSynthetic: directed.every((asset) => asset.synthetic),
    }),
    warnings,
  };
}

function rankProviders(
  context: AssetGenerationContext,
  providers: AssetGenerationProvider[],
): AssetGenerationProvider[] {
  const capable = providers.filter((provider) => provider.canHandle(context));

  // Maya's hook should feel like a person speaking to camera. Prefer the avatar
  // provider there. Other generated-image beats prefer cinematic B-roll.
  if (context.brand.id === 'maya' && context.isHook) {
    return capable.sort((a, b) => providerPriority(a.id, ['heygen', 'runway']) - providerPriority(b.id, ['heygen', 'runway']));
  }

  if (context.asset.type === 'generated_image') {
    return capable.sort((a, b) => providerPriority(a.id, ['runway', 'heygen']) - providerPriority(b.id, ['runway', 'heygen']));
  }

  return capable;
}

function providerPriority(id: string, order: string[]): number {
  const index = order.indexOf(id);
  return index === -1 ? order.length : index;
}

function defaultProviders(config: BrandProviderConfig): AssetGenerationProvider[] {
  const providers: AssetGenerationProvider[] = [];
  const heygenKey = process.env.HEYGEN_API_KEY?.trim();
  const runwayKey = process.env.RUNWAYML_API_SECRET?.trim();

  if (heygenKey && config.heygen?.enabled !== false && config.heygen?.avatarId) {
    providers.push(buildHeyGenProvider(heygenKey, config));
  }
  if (runwayKey && config.runway?.enabled !== false) {
    providers.push(buildRunwayImageProvider(runwayKey, config));
  }

  return providers;
}

function buildHeyGenProvider(apiKey: string, config: BrandProviderConfig): AssetGenerationProvider {
  return {
    id: 'heygen',
    canHandle(context) {
      if (!context.config.heygen?.avatarId) return false;
      if (context.asset.type !== 'generated_image') return false;
      const configuredScenes = context.config.heygen.talkingHeadSceneNumbers ?? [1];
      return context.brand.id === 'maya' && configuredScenes.includes(context.scene.sceneNumber);
    },
    async generate(context) {
      const heygen = context.config.heygen!;
      const create = await fetchJson('https://api.heygen.com/v3/videos', {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-api-key': apiKey,
        },
        body: JSON.stringify({
          type: 'avatar',
          avatar_id: heygen.avatarId,
          title: `${context.brand.name} - scene ${context.scene.sceneNumber}`,
          aspect_ratio: '9:16',
          resolution: heygen.resolution ?? '720p',
          output_format: 'mp4',
          script: context.scene.voiceover,
          ...(heygen.voiceId ? { voice_id: heygen.voiceId } : {}),
          caption: { file_format: 'srt' },
        }),
      });

      const createData = objectData(create);
      const videoId = stringValue(createData.video_id) ?? stringValue(createData.id);
      if (!videoId) throw new Error('create response did not contain a video id');

      const detail = await poll(
        async () => objectData(await fetchJson(`https://api.heygen.com/v3/videos/${videoId}`, {
          headers: { 'x-api-key': apiKey },
        })),
        (value) => stringValue(value.status),
        new Set(['completed']),
        new Set(['failed']),
      );

      const uri = stringValue(detail.video_url);
      if (!uri) throw new Error('completed video did not contain video_url');

      return {
        uri,
        mediaKind: 'video',
        provider: 'heygen',
        note: `avatar talking-head; duration=${numberValue(detail.duration) ?? 'unknown'}s`,
      };
    },
  };
}

function buildRunwayImageProvider(apiKey: string, config: BrandProviderConfig): AssetGenerationProvider {
  return {
    id: 'runway',
    canHandle(context) {
      return context.asset.type === 'generated_image';
    },
    async generate(context) {
      const runway = context.config.runway ?? {};
      const prompt = realismPrompt(context);
      const create = await fetchJson('https://api.dev.runwayml.com/v1/text_to_image', {
        method: 'POST',
        headers: {
          authorization: `Bearer ${apiKey}`,
          'content-type': 'application/json',
          'x-runway-version': RUNWAY_API_VERSION,
        },
        body: JSON.stringify({
          model: runway.model ?? DEFAULT_RUNWAY_MODEL,
          promptText: prompt,
          ratio: runway.ratio ?? DEFAULT_RUNWAY_RATIO,
        }),
      });

      const taskId = stringValue((create as Record<string, unknown>).id)
        ?? stringValue(objectData(create).id);
      if (!taskId) throw new Error('create response did not contain a task id');

      const detail = await poll(
        async () => await fetchJson(`https://api.dev.runwayml.com/v1/tasks/${taskId}`, {
          headers: {
            authorization: `Bearer ${apiKey}`,
            'x-runway-version': RUNWAY_API_VERSION,
          },
        }) as Record<string, unknown>,
        (value) => stringValue(value.status),
        new Set(['SUCCEEDED']),
        new Set(['FAILED', 'CANCELLED']),
      );

      const output = Array.isArray(detail.output) ? detail.output : [];
      const uri = output.find((item): item is string => typeof item === 'string');
      if (!uri) throw new Error('completed image task did not contain an output URL');

      return {
        uri,
        mediaKind: 'image',
        provider: 'runway',
        note: 'photoreal beauty/lifestyle B-roll; not evidence of real product use',
      };
    },
  };
}

function realismPrompt(context: AssetGenerationContext): string {
  return [
    context.scene.visualDescription,
    context.asset.description,
    'Vertical 9:16 creator-style beauty content.',
    'Photorealistic materials and natural smartphone-camera exposure.',
    'Soft window light mixed with believable room light, subtle depth of field.',
    'Avoid glossy CGI skin, plastic textures, impossible reflections, warped packaging, extra fingers, or fake text.',
    'No logos and no readable text. Leave clean negative space for captions added later in Remotion.',
    'The image is illustrative B-roll, not proof that a physical product was bought, worn, or tested.',
  ].join(' ');
}

function loadProviderConfig(brandId: string, brandsDirectory?: string): BrandProviderConfig {
  const dir = resolve(brandsDirectory ?? process.env.BRANDS_DIR ?? './brands');
  const path = join(dir, brandId, 'providers.json');
  if (!existsSync(path)) return {};

  try {
    return JSON.parse(readFileSync(path, 'utf8')) as BrandProviderConfig;
  } catch (error) {
    throw new Error(`invalid provider config ${path}: ${(error as Error).message}`);
  }
}

async function fetchJson(url: string, init: RequestInit = {}): Promise<unknown> {
  const response = await fetch(url, init);
  const text = await response.text();
  let payload: unknown = {};
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = { raw: text };
    }
  }

  if (!response.ok) {
    const message = errorMessage(payload) ?? response.statusText;
    throw new Error(`${response.status} ${message}`.trim());
  }
  return payload;
}

async function poll<T extends Record<string, unknown>>(
  read: () => Promise<T>,
  statusOf: (value: T) => string | null,
  success: Set<string>,
  failure: Set<string>,
): Promise<T> {
  const pollMs = positiveInt(process.env.MEDIA_PROVIDER_POLL_MS, DEFAULT_POLL_MS);
  const maxPolls = positiveInt(process.env.MEDIA_PROVIDER_MAX_POLLS, DEFAULT_MAX_POLLS);

  for (let attempt = 0; attempt < maxPolls; attempt += 1) {
    const value = await read();
    const status = statusOf(value);
    if (status && success.has(status)) return value;
    if (status && failure.has(status)) {
      throw new Error(errorMessage(value) ?? `provider job failed with status ${status}`);
    }
    if (attempt < maxPolls - 1) await sleep(pollMs);
  }

  throw new Error(`provider job did not complete after ${maxPolls} polls`);
}

function objectData(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object') return {};
  const record = value as Record<string, unknown>;
  if (record.data && typeof record.data === 'object' && !Array.isArray(record.data)) {
    return record.data as Record<string, unknown>;
  }
  return record;
}

function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function numberValue(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function errorMessage(value: unknown): string | null {
  const record = objectData(value);
  return stringValue(record.failure_message)
    ?? stringValue(record.message)
    ?? stringValue((record.error as Record<string, unknown> | undefined)?.message);
}

function positiveInt(raw: string | undefined, fallback: number): number {
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolveSleep) => setTimeout(resolveSleep, ms));
}
