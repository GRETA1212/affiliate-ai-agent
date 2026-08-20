import type { z } from 'zod';
import { LlmError, type LlmProvider, type LlmRequest } from './provider.ts';

export type MockHandler = (request: LlmRequest) => unknown;

/**
 * Offline, deterministic provider. This is the default and is what the test
 * suite uses, so the project runs end to end with no API key and no network.
 * Content generators register handlers keyed by task name.
 */
export class MockLlmProvider implements LlmProvider {
  readonly name = 'mock';
  private readonly handlers = new Map<string, MockHandler>();

  register(task: string, handler: MockHandler): this {
    this.handlers.set(task, handler);
    return this;
  }

  async generateJson<T>(request: LlmRequest, schema: z.ZodType<T>): Promise<T> {
    const handler = this.handlers.get(request.task);
    if (!handler) {
      throw new LlmError(`no mock handler registered for task "${request.task}"`, this.name);
    }
    const parsed = schema.safeParse(handler(request));
    if (!parsed.success) {
      throw new LlmError(
        `mock output failed schema for "${request.task}": ${parsed.error.message}`,
        this.name,
      );
    }
    return parsed.data;
  }
}
