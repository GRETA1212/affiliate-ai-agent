import { describe, expect, it } from 'vitest';
import { directAssets, type AssetGenerationProvider } from '../packages/agents/asset-director.ts';
import { planAssets } from '../packages/agents/asset-planner.ts';
import { loadBrand } from '../packages/core/brand.ts';
import { ContentBriefSchema, ScriptSchema, StoryboardSchema } from '../packages/core/types.ts';
import { buildRenderInput } from '../packages/renderer/build-render-input.ts';

const maya = loadBrand('maya');

const storyboard = StoryboardSchema.parse({
  id: 'sb_asset_director',
  scriptId: 'script_asset_director',
  brandId: 'maya',
  totalDurationSeconds: 24,
  createdAt: '2026-08-20T00:00:00.000Z',
  scenes: [
    {
      sceneNumber: 1,
      durationSeconds: 8,
      voiceover: 'I let an AI plan this makeup look. Here is the first decision.',
      onScreenText: 'THE PLAN',
      visualDescription: 'Maya speaking directly to camera in a believable home vanity setup.',
      assetRequirements: ['generated_image: creator hook visual', 'text_graphic: hook typography'],
      transition: 'whip',
    },
    {
      sceneNumber: 2,
      durationSeconds: 8,
      voiceover: 'The next step is easier to understand when you can actually see it.',
      onScreenText: 'THE STEP',
      visualDescription: 'Photoreal vanity B-roll showing the makeup step without readable packaging text.',
      assetRequirements: ['generated_image: realistic beauty b-roll', 'text_graphic: panel label'],
      transition: 'cut',
    },
    {
      sceneNumber: 3,
      durationSeconds: 8,
      voiceover: 'Full breakdown is in the link in bio.',
      onScreenText: 'FULL BREAKDOWN',
      visualDescription: 'Closing CTA card.',
      assetRequirements: ['text_graphic: CTA card'],
      transition: 'fade',
    },
  ],
});

const brief = ContentBriefSchema.parse({
  id: 'brief_asset_director',
  brandId: 'maya',
  topic: 'AI chooses a makeup look',
  format: 'demo_walkthrough',
  hook: 'I let an AI plan this makeup look.',
  audience: maya.audience,
  angle: 'Show the plan and its limitation.',
  cta: maya.defaultCta,
  monetizationPath: 'affiliate',
  keyPoints: ['Show the plan', 'Name the limitation'],
  targetDurationSeconds: 24,
  requiredDisclosures: ['Virtual AI creator'],
  createdAt: '2026-08-20T00:00:00.000Z',
});

const script = ScriptSchema.parse({
  id: 'script_asset_director',
  briefId: brief.id,
  brandId: 'maya',
  title: 'Maya.exe: AI chooses a makeup look',
  hook: brief.hook,
  cta: brief.cta,
  totalDurationSeconds: 24,
  disclosures: ['Virtual AI creator'],
  createdAt: '2026-08-20T00:00:00.000Z',
  lines: storyboard.scenes.map((scene) => ({
    sceneNumber: scene.sceneNumber,
    voiceover: scene.voiceover,
    onScreenText: scene.onScreenText,
    durationSeconds: scene.durationSeconds,
    sourceId: null,
  })),
});

function fakeProvider(id: 'heygen' | 'runway'): AssetGenerationProvider {
  return {
    id,
    canHandle(context) {
      if (context.asset.type !== 'generated_image') return false;
      return id === 'heygen' ? context.isHook : true;
    },
    async generate(context) {
      return id === 'heygen'
        ? {
            uri: 'https://media.example.test/maya-hook.mp4',
            mediaKind: 'video' as const,
            provider: 'heygen',
          }
        : {
            uri: `https://media.example.test/scene-${context.scene.sceneNumber}.jpg`,
            mediaKind: 'image' as const,
            provider: 'runway',
          };
    },
  };
}

describe('asset director', () => {
  it('routes Maya hook to avatar video, B-roll to image generation, and text to Remotion', async () => {
    const planned = planAssets({ storyboard, mode: 'synthetic' });
    const result = await directAssets({
      brand: maya,
      storyboard,
      assetPlan: planned,
      providers: [fakeProvider('runway'), fakeProvider('heygen')],
    });

    const hookVisual = result.assetPlan.assets.find(
      (asset) => asset.sceneNumber === 1 && asset.type === 'generated_image',
    );
    const broll = result.assetPlan.assets.find(
      (asset) => asset.sceneNumber === 2 && asset.type === 'generated_image',
    );
    const hookText = result.assetPlan.assets.find(
      (asset) => asset.sceneNumber === 1 && asset.type === 'text_graphic',
    );

    expect(hookVisual?.status).toBe('ready');
    expect(hookVisual?.uri).toMatch(/\.mp4$/);
    expect(hookVisual?.sourceNote).toMatch(/provider:heygen/);

    expect(broll?.status).toBe('ready');
    expect(broll?.uri).toMatch(/\.jpg$/);
    expect(broll?.sourceNote).toMatch(/provider:runway/);

    expect(hookText?.status).toBe('ready');
    expect(hookText?.uri).toBeNull();
    expect(hookText?.sourceNote).toMatch(/provider:remotion/);
    expect(result.warnings).toEqual([]);
  });

  it('keeps placeholders honest when no external providers are available', async () => {
    const planned = planAssets({ storyboard, mode: 'synthetic' });
    const result = await directAssets({ brand: maya, storyboard, assetPlan: planned, providers: [] });

    const visualAssets = result.assetPlan.assets.filter((asset) => asset.type === 'generated_image');
    expect(visualAssets.every((asset) => asset.status === 'placeholder')).toBe(true);
    expect(visualAssets.every((asset) => asset.uri === null)).toBe(true);
  });

  it('hands real provider media through to the Remotion runtime contract', async () => {
    const planned = planAssets({ storyboard, mode: 'synthetic' });
    const directed = await directAssets({
      brand: maya,
      storyboard,
      assetPlan: planned,
      providers: [fakeProvider('runway'), fakeProvider('heygen')],
    });

    const input = buildRenderInput({
      jobId: 'job_asset_director',
      brand: maya,
      brief,
      script,
      storyboard,
      assetPlan: directed.assetPlan,
    });

    const scenes = input.scenes as Array<(typeof input.scenes)[number] & {
      assetUri?: string | null;
      assetMediaKind?: 'image' | 'video' | 'graphic' | null;
    }>;

    expect(scenes[0]?.assetUri).toBe('https://media.example.test/maya-hook.mp4');
    expect(scenes[0]?.assetMediaKind).toBe('video');
    expect(scenes[1]?.assetUri).toBe('https://media.example.test/scene-2.jpg');
    expect(scenes[1]?.assetMediaKind).toBe('image');
  });
});
