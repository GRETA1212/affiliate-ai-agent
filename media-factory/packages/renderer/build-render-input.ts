import { wrapText } from '../core/text.ts';
import {
  RenderInputSchema,
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
  const assetsByScene = new Map(assetPlan.assets.map((a) => [a.sceneNumber, a]));
  const lastSceneNumber = storyboard.scenes[storyboard.scenes.length - 1]?.sceneNumber;

  const scenes = storyboard.scenes.map((scene, index) => {
    const asset = assetsByScene.get(scene.sceneNumber);
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
    };
  });

  const totalFrames = scenes.reduce((sum, s) => sum + s.durationFrames, 0);

  const disclosure = brand.rules.requireAiDisclosure ? brand.rules.aiDisclosureText : null;
  const paid = brief.monetizationPath === 'affiliate' || brief.monetizationPath === 'sponsorship';
  const affiliate = brand.rules.requireAffiliateDisclosure && paid ? brand.rules.affiliateDisclosureText : null;

  return RenderInputSchema.parse({
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
    scenes,
    audio: {
      trackPath: args.audioTrackPath ?? null,
      placeholderSilence: !args.audioTrackPath,
    },
  });
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
