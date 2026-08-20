import type { z } from 'zod';
import { LlmError, parseJsonLoose, type LlmProvider, type LlmRequest } from './provider.ts';

/**
 * Thin HTTP providers. They are optional: nothing in the test suite or the demo
 * pipeline touches them, and no key is ever read at import time.
 */

const JSON_INSTRUCTION =
  'Respond with a single valid JSON object only. No prose, no markdown fences.';

async function validate<T>(raw: string, schema: z.ZodType<T>, provider: string, task: string): Promise<T> {
  let parsedJson: unknown;
  try {
    parsedJson = parseJsonLoose(raw);
  } catch (cause) {
    throw new LlmError(`${provider} returned non-JSON for "${task}"`, provider, cause);
  }
  const result = schema.safeParse(parsedJson);
  if (!result.success) {
    throw new LlmError(`${provider} output failed schema for "${task}": ${result.error.message}`, provider);
  }
  return result.data;
}

export class AnthropicProvider implements LlmProvider {
  readonly name = 'anthropic';
  constructor(
    private readonly apiKey: string,
    private readonly model = process.env.ANTHROPIC_MODEL ?? 'claude-sonnet-4-5',
  ) {
    if (!apiKey) throw new LlmError('ANTHROPIC_API_KEY is not set', this.name);
  }

  async generateJson<T>(request: LlmRequest, schema: z.ZodType<T>): Promise<T> {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': this.apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: this.model,
        max_tokens: request.maxTokens ?? 2000,
        system: `${request.system}\n\n${JSON_INSTRUCTION}`,
        messages: [{ role: 'user', content: request.prompt }],
      }),
    });
    if (!response.ok) {
      throw new LlmError(`anthropic http ${response.status}`, this.name, await response.text());
    }
    const body = (await response.json()) as { content: { type: string; text?: string }[] };
    const text = body.content.filter((b) => b.type === 'text').map((b) => b.text ?? '').join('');
    return validate(text, schema, this.name, request.task);
  }
}

export class OpenAiProvider implements LlmProvider {
  readonly name = 'openai';
  constructor(
    private readonly apiKey: string,
    private readonly model = process.env.OPENAI_MODEL ?? 'gpt-4o-mini',
  ) {
    if (!apiKey) throw new LlmError('OPENAI_API_KEY is not set', this.name);
  }

  async generateJson<T>(request: LlmRequest, schema: z.ZodType<T>): Promise<T> {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${this.apiKey}` },
      body: JSON.stringify({
        model: this.model,
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: `${request.system}\n\n${JSON_INSTRUCTION}` },
          { role: 'user', content: request.prompt },
        ],
      }),
    });
    if (!response.ok) {
      throw new LlmError(`openai http ${response.status}`, this.name, await response.text());
    }
    const body = (await response.json()) as { choices: { message: { content: string } }[] };
    return validate(body.choices[0]?.message.content ?? '', schema, this.name, request.task);
  }
}

export class OllamaProvider implements LlmProvider {
  readonly name = 'ollama';
  constructor(
    private readonly baseUrl = process.env.OLLAMA_BASE_URL ?? 'http://localhost:11434',
    private readonly model = process.env.OLLAMA_MODEL ?? 'llama3.1',
  ) {}

  async generateJson<T>(request: LlmRequest, schema: z.ZodType<T>): Promise<T> {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        model: this.model,
        format: 'json',
        stream: false,
        messages: [
          { role: 'system', content: `${request.system}\n\n${JSON_INSTRUCTION}` },
          { role: 'user', content: request.prompt },
        ],
      }),
    });
    if (!response.ok) {
      throw new LlmError(`ollama http ${response.status}`, this.name, await response.text());
    }
    const body = (await response.json()) as { message: { content: string } };
    return validate(body.message.content, schema, this.name, request.task);
  }
}
