import { llmRequest, type LlmProvider } from '../core/llm/provider.ts';
import { now, stableId } from '../core/ids.ts';
import { ContentBriefSchema, type Brand, type ContentBrief, type Fact } from '../core/types.ts';
import { BriefDraftSchema, TASKS } from '../content/schemas.ts';
import { briefPrompt, systemPrompt } from '../content/prompts.ts';

export interface StrategistOptions {
  brand: Brand;
  topic: string;
  facts: Fact[];
  provider: LlmProvider;
  /** True when no real footage exists, which changes what the copy may claim. */
  syntheticAssets: boolean;
  targetDurationSeconds?: number;
}

/** Picks format, hook, angle, CTA and the monetization path for a topic. */
export async function planContent(options: StrategistOptions): Promise<ContentBrief> {
  const { brand, topic } = options;
  const targetDurationSeconds =
    options.targetDurationSeconds ??
    Math.round((brand.rules.minDurationSeconds + brand.rules.maxDurationSeconds) / 2 - 10);

  const input = {
    topic,
    syntheticAssets: options.syntheticAssets,
    facts: options.facts,
    brand: brandContext(brand, targetDurationSeconds),
  };

  const draft = await options.provider.generateJson(
    llmRequest({
      task: TASKS.brief,
      system: systemPrompt(brand),
      seed: `${brand.id}:${topic}:brief`,
      input,
      instruction: briefPrompt({
        topic,
        targetDurationSeconds,
        monetizationPaths: brand.monetizationPaths,
        facts: options.facts,
        brand,
      }),
    }),
    BriefDraftSchema,
  );

  const requiredDisclosures: string[] = [];
  if (brand.rules.requireAiDisclosure) requiredDisclosures.push(brand.rules.aiDisclosureText);
  if (brand.rules.requireAffiliateDisclosure && isPaidPath(draft.monetizationPath)) {
    requiredDisclosures.push(brand.rules.affiliateDisclosureText);
  }

  return ContentBriefSchema.parse({
    id: stableId('brief', brand.id, topic),
    brandId: brand.id,
    topic,
    format: draft.format,
    hook: draft.hook,
    audience: draft.audience,
    angle: draft.angle,
    cta: draft.cta,
    monetizationPath: draft.monetizationPath,
    keyPoints: draft.keyPoints,
    targetDurationSeconds,
    requiredDisclosures,
    createdAt: now(),
  });
}

export function isPaidPath(path: string): boolean {
  return path === 'affiliate' || path === 'sponsorship';
}

export function brandContext(brand: Brand, targetDurationSeconds: number) {
  return {
    id: brand.id,
    name: brand.name,
    audience: brand.audience,
    defaultCta: brand.defaultCta,
    monetizationPaths: brand.monetizationPaths,
    childDirected: brand.rules.childDirected,
    targetDurationSeconds,
    minSceneSeconds: brand.rules.minSceneSeconds,
    maxSceneSeconds: brand.rules.maxSceneSeconds,
  };
}
