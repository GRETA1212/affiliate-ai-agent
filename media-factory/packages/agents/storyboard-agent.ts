import { llmRequest, type LlmProvider } from '../core/llm/provider.ts';
import { now, stableId } from '../core/ids.ts';
import { StoryboardSchema, type Brand, type Script, type Storyboard } from '../core/types.ts';
import { StoryboardDraftSchema, TASKS } from '../content/schemas.ts';
import { storyboardPrompt, systemPrompt } from '../content/prompts.ts';
import { brandContext } from './content-strategist.ts';

export interface StoryboardOptions {
  brand: Brand;
  script: Script;
  provider: LlmProvider;
}

/** Expands the script into per-scene visual instructions the renderer can use. */
export async function buildStoryboard(options: StoryboardOptions): Promise<Storyboard> {
  const { brand, script } = options;

  const input = {
    script: {
      title: script.title,
      hook: script.hook,
      cta: script.cta,
      lines: script.lines,
    },
    signature: brand.theme.signature,
    brand: brandContext(brand, script.totalDurationSeconds),
  };

  const draft = await options.provider.generateJson(
    llmRequest({
      task: TASKS.storyboard,
      system: systemPrompt(brand),
      seed: `${brand.id}:${script.id}:storyboard`,
      input,
      instruction: storyboardPrompt({ script: input.script, signature: brand.theme.signature }),
    }),
    StoryboardDraftSchema,
  );

  const totalDurationSeconds = Number(
    draft.scenes.reduce((sum, scene) => sum + scene.durationSeconds, 0).toFixed(2),
  );

  return StoryboardSchema.parse({
    id: stableId('sb', brand.id, script.id),
    scriptId: script.id,
    brandId: brand.id,
    scenes: draft.scenes,
    totalDurationSeconds,
    createdAt: now(),
  });
}
