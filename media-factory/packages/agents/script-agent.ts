import { llmRequest, type LlmProvider } from '../core/llm/provider.ts';
import { now, stableId } from '../core/ids.ts';
import { ScriptSchema, type Brand, type ContentBrief, type Fact, type Script } from '../core/types.ts';
import { ScriptDraftSchema, TASKS } from '../content/schemas.ts';
import { scriptPrompt, systemPrompt } from '../content/prompts.ts';
import { brandContext } from './content-strategist.ts';

export interface ScriptOptions {
  brand: Brand;
  brief: ContentBrief;
  facts: Fact[];
  provider: LlmProvider;
  allSynthetic: boolean;
  sceneCount?: number;
}

/** Writes the structured short-form script. Output is schema-validated JSON. */
export async function writeScript(options: ScriptOptions): Promise<Script> {
  const { brand, brief } = options;
  const verifiedFacts = options.facts.filter((f) => f.kind === 'verified_fact');
  const assumptions = options.facts.filter((f) => f.kind === 'assumption');
  const sceneCount = options.sceneCount ?? defaultSceneCount(brief.targetDurationSeconds);

  const input = {
    brief: { ...brief },
    facts: verifiedFacts,
    assumptions,
    allSynthetic: options.allSynthetic,
    sceneCount,
    targetDurationSeconds: brief.targetDurationSeconds,
    brand: brandContext(brand, brief.targetDurationSeconds),
  };

  const draft = await options.provider.generateJson(
    llmRequest({
      task: TASKS.script,
      system: systemPrompt(brand),
      seed: `${brand.id}:${brief.topic}:script`,
      input,
      instruction: scriptPrompt({
        brief,
        facts: verifiedFacts,
        assumptions,
        allSynthetic: options.allSynthetic,
        sceneCount,
        targetDurationSeconds: brief.targetDurationSeconds,
        brand,
      }),
    }),
    ScriptDraftSchema,
  );

  const totalDurationSeconds = Number(
    draft.lines.reduce((sum, line) => sum + line.durationSeconds, 0).toFixed(2),
  );

  return ScriptSchema.parse({
    id: stableId('script', brand.id, brief.topic),
    briefId: brief.id,
    brandId: brand.id,
    title: draft.title,
    hook: draft.hook,
    cta: draft.cta,
    lines: draft.lines,
    totalDurationSeconds,
    disclosures: brief.requiredDisclosures,
    createdAt: now(),
  });
}

/**
 * Scene budget.
 *
 * A beat every ~5.5s is the pacing that actually fits: at a 2.6 words-per-second
 * speaking rate, a 5.5s beat is about 14 words, which is one clean sentence.
 * Budgeting tighter than this produced scripts that overshot their target
 * duration, because each scene still has to be long enough to speak its line.
 */
export function defaultSceneCount(targetDurationSeconds: number): number {
  return Math.max(3, Math.min(8, Math.round(targetDurationSeconds / 5.5)));
}
