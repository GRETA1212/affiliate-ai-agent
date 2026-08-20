import { now, stableId } from '../core/ids.ts';
import { AssetPlanSchema, type AssetPlan, type AssetType, type Storyboard } from '../core/types.ts';

export type AssetMode = 'synthetic' | 'mixed';

export interface AssetPlanOptions {
  storyboard: Storyboard;
  /**
   * 'synthetic' means nothing was filmed or physically tested. The plan records
   * that fact, and the QA agent uses it to block first-person testing claims.
   */
  mode?: AssetMode;
  /** Scene numbers with real, captured footage available. Only used in 'mixed'. */
  realFootageScenes?: number[];
}

const TYPE_HINTS: { pattern: RegExp; type: AssetType }[] = [
  { pattern: /screen recording|app ui|interface capture/i, type: 'screen_recording' },
  { pattern: /product b-?roll|packaging|bottle|tube/i, type: 'product_broll' },
  { pattern: /stock footage|stock clip/i, type: 'stock_footage' },
  { pattern: /animation|motion|arrow|transition graphic/i, type: 'animation' },
  { pattern: /text graphic|typography|caption card|label/i, type: 'text_graphic' },
  { pattern: /generated image|mockup|render|illustration|texture/i, type: 'generated_image' },
];

/** Decides what each scene needs and marks honestly whether it is synthetic. */
export function planAssets(options: AssetPlanOptions): AssetPlan {
  const mode = options.mode ?? 'synthetic';
  const realScenes = new Set(options.realFootageScenes ?? []);

  const assets = options.storyboard.scenes.flatMap((scene) =>
    scene.assetRequirements.map((requirement, index) => {
      const type = classify(requirement);
      const isReal = mode === 'mixed' && realScenes.has(scene.sceneNumber) && type !== 'text_graphic';
      return {
        id: stableId('asset', options.storyboard.id, scene.sceneNumber, index),
        sceneNumber: scene.sceneNumber,
        type,
        description: requirement,
        synthetic: !isReal,
        status: 'placeholder' as const,
        uri: null,
        sourceNote: isReal
          ? 'captured footage - operator must attach the file before render'
          : 'synthetic asset - no physical product was used, worn, or tested',
      };
    }),
  );

  return AssetPlanSchema.parse({
    id: stableId('plan', options.storyboard.id),
    storyboardId: options.storyboard.id,
    assets,
    allSynthetic: assets.every((asset) => asset.synthetic),
    createdAt: now(),
  });
}

export function classify(requirement: string): AssetType {
  for (const hint of TYPE_HINTS) {
    if (hint.pattern.test(requirement)) return hint.type;
  }
  return 'generated_image';
}
