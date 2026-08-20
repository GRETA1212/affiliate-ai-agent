import { buildMockProvider } from '../../content/mock-content.ts';
import { loadLocalEnv } from '../env.ts';
import { AnthropicProvider, OllamaProvider, OpenAiProvider } from './http.ts';
import { LlmError, type LlmProvider } from './provider.ts';

// CLI users are explicitly told to configure .env. Load it once here before
// provider selection; shell/CI variables still win because loadLocalEnv never
// overwrites an existing process.env value.
loadLocalEnv();

export type ProviderName = 'mock' | 'anthropic' | 'openai' | 'ollama';

/**
 * Resolves the provider from the environment. The default is `mock`, so a fresh
 * clone with no .env runs the entire pipeline and the whole test suite offline
 * with no API key and no network.
 */
export function createProvider(name: string = process.env.LLM_PROVIDER ?? 'mock'): LlmProvider {
  switch (name as ProviderName) {
    case 'mock':
      return buildMockProvider();
    case 'anthropic':
      return new AnthropicProvider(process.env.ANTHROPIC_API_KEY ?? '');
    case 'openai':
      return new OpenAiProvider(process.env.OPENAI_API_KEY ?? '');
    case 'ollama':
      return new OllamaProvider();
    default:
      throw new LlmError(`unknown LLM_PROVIDER "${name}"`, 'factory');
  }
}

export * from './provider.ts';
export { MockLlmProvider } from './mock.ts';