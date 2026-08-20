import type { z } from 'zod';

export interface LlmRequest {
  /** Stable identifier for the task, used by the mock provider to route. */
  task: string;
  system: string;
  prompt: string;
  /** Deterministic seed so mock output is reproducible. */
  seed: string;
  /**
   * Structured task input. HTTP providers serialise it into the prompt; the
   * mock provider reads it directly. One contract, no drift between modes.
   */
  input: Record<string, unknown>;
  maxTokens?: number;
}

/** Builds a request whose prompt always mirrors the structured input. */
export function llmRequest(args: {
  task: string;
  system: string;
  input: Record<string, unknown>;
  seed: string;
  instruction: string;
  maxTokens?: number;
}): LlmRequest {
  return {
    task: args.task,
    system: args.system,
    seed: args.seed,
    input: args.input,
    maxTokens: args.maxTokens,
    prompt: `${args.instruction}\n\nINPUT:\n${JSON.stringify(args.input, null, 2)}`,
  };
}

export interface LlmProvider {
  readonly name: string;
  /**
   * Returns JSON matching `schema`. Implementations must validate before
   * returning so a bad model response never propagates into the pipeline.
   */
  generateJson<T>(request: LlmRequest, schema: z.ZodType<T>): Promise<T>;
}

export class LlmError extends Error {
  constructor(message: string, readonly provider: string, readonly cause?: unknown) {
    super(message);
    this.name = 'LlmError';
  }
}

/** Strips markdown fences some models wrap around JSON. */
export function parseJsonLoose(raw: string): unknown {
  const cleaned = raw.trim().replace(/^```(?:json)?/i, '').replace(/```$/, '').trim();
  const start = cleaned.indexOf('{');
  const end = cleaned.lastIndexOf('}');
  const slice = start >= 0 && end > start ? cleaned.slice(start, end + 1) : cleaned;
  return JSON.parse(slice);
}
