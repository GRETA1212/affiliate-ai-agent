import { wrapText } from '../core/text.ts';
import {
  RenderInputSchema,
  type Asset,
  type AssetPlan,
  type Brand,
  type ContentBrief,
  type RenderInput,
  type Script,
  type Storyboard,
} from '../core/types.ts';

export const FPS = 30 as const;
export const WIDTH = 1080 as const;
export const HEIGHT = 1920 as const;

/**
 * Runtime-only media fields deliberately stay outside the core zod schema for
 * now. Older saved render inputs therefore remain valid, while newly directed
 * jobs can hand a real image/video URL to Remotion. Once the provider contract
 * stabilises these can graduate into core/types without breaking old jobs.
 */
export interface RuntimeMediaFields {
  assetUri: string | null;
  assetSourceNote: string | null;
  assetMediaKind: 'image' | 'video' | 'graphic' | null;
}

/**
 * The single source of truth for what gets drawn.
 *
 * Both renderers consume this object, so the ffmpeg fallback and the Remotion
 * composition cannot drift on timing, captions or badges. It is validated by
 * zod, which is what `tests/renderer-input.test.ts` asserts against.
 */
export function buildRenderInput(args: {
  jobId: string;
  brand: Brand;
  brief: ContentBrief;
  script: Script;
  storyboard: Storyboard;
  assetPlan: AssetPlan;
  audioTrackPath?: string | null;
}): RenderInput {
  const { jobId, brand, brief, script, storyboard, assetPlan } = args;
  const assetsByScene = groupAssetsByScene(assetPlan.assets);
  const lastSceneNumber = storyboard.scenes[storyboard.scenes.length - 1]?.sceneNumber;

  const candidateScenes = storyboard.scenes.map((scene, index) => {
    const assets = assetsByScene.get(scene.sceneNumber) ?? [];
    // Prefer an actually generated visual, then a non-typography visual, then
    // the first planned asset. The old Map(scene -> asset) silently chose the
    // last asset, which was often the text card instead of the visual itself.
    const asset = assets.find((item) => item.status === 'ready' && Boolean(item.uri))
      ?? assets.find((item) => item.type !== 'text_graphic')
      ?? assets[0];

    // Frames are the unit of truth. Rounding once here keeps the audio bed, the
    // caption timings and the total length in agreement.
    const durationFrames = Math.max(1, Math.round(scene.durationSeconds * FPS));
    return {
      index,
      sceneNumber: scene.sceneNumber,
      durationSeconds: scene.durationSeconds,
      durationFrames,
      onScreenText: scene.onScreenText,
      captionLines: wrapText(scene.onScreenText, brand.rules.maxCaptionCharsPerLine),
      visualDescription: scene.visualDescription,
      assetType: asset?.type ?? 'text_graphic',
      assetStatus: asset?.status ?? 'placeholder',
      transition: scene.transition,
      isHook: index === 0,
      isCta: scene.sceneNumber === lastSceneNumber,
      assetUri: asset?.uri ?? null,
      assetSourceNote: asset?.sourceNote ?? null,
      assetMediaKind: mediaKind(asset),
    };
  });

  const totalFrames = candidateScenes.reduce((sum, s) => sum + s.durationFrames, 0);

  const disclosure = brand.rules.requireAiDisclosure ? brand.rules.aiDisclosureText : null;
  const paid = brief.monetizationPath === 'affiliate' || brief.monetizationPath === 'sponsorship';
  const affiliate = brand.rules.requireAffiliateDisclosure && paid ? brand.rules.affiliateDisclosureText : null;

  // Validate the stable contract first. Zod strips the runtime extension, so we
  // add it back after validation. JSON.stringify then preserves the real media
  // URLs for Remotion while old consumers still see a valid RenderInput.
  const validated = RenderInputSchema.parse({
    jobId,
    brandId: brand.id,
    brandName: brand.name,
    title: script.title,
    width: WIDTH,
    height: HEIGHT,
    fps: FPS,
    totalFrames,
    hookText: script.hook,
    ctaText: script.cta,
    badges: { brand: brand.name, disclosure, affiliate },
    theme: brand.theme,
    scenes: candidateScenes,
    audio: {
      trackPath: args.audioTrackPath ?? null,
      placeholderSilence: !args.audioTrackPath,
    },
  });

  return {
    ...validated,
    scenes: validated.scenes.map((scene, index) => ({
      ...scene,
      assetUri: candidateScenes[index]?.assetUri ?? null,
      assetSourceNote: candidateScenes[index]?.assetSourceNote ?? null,
      assetMediaKind: candidateScenes[index]?.assetMediaKind ?? null,
    })),
  } as RenderInput;
}

function groupAssetsByScene(assets: Asset[]): Map<number, Asset[]> {
  const grouped = new Map<number, Asset[]>();
  for (const asset of assets) {
    const current = grouped.get(asset.sceneNumber) ?? [];
    current.push(asset);
    grouped.set(asset.sceneNumber, current);
  }
  return grouped;
}

function mediaKind(asset: Asset | undefined): RuntimeMediaFields['assetMediaKind'] {
  if (!asset) return null;
  if (asset.type === 'text_graphic') return 'graphic';

  const note = asset.sourceNote ?? '';
  if (/media:video/i.test(note)) return 'video';
  if (/media:image/i.test(note)) return 'image';

  const uri = asset.uri?.split('?')[0]?.toLowerCase() ?? '';
  if (/\.(mp4|webm|mov)$/.test(uri)) return 'video';
  if (/\.(png|jpe?g|webp|gif)$/.test(uri)) return 'image';
  return asset.uri ? 'image' : null;
}

/** Frame index where each scene starts. Used for thumbnails and QA. */
export function sceneStartFrames(input: RenderInput): number[] {
  const starts: number[] = [];
  let cursor = 0;
  for (const scene of input.scenes) {
    starts.push(cursor);
    cursor += scene.durationFrames;
  }
  return starts;
}

/**
 * Thumbnail suggestion: the frame at the visual midpoint of the hook scene.
 * The hook is what stops the scroll, so it is what the still should show.
 */
export function thumbnailFrame(input: RenderInput): number {
  const hook = input.scenes.find((s) => s.isHook) ?? input.scenes[0];
  if (!hook) return 0;
  return Math.floor(hook.durationFrames / 2);
}
