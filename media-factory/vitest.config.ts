import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';

const r = (p: string) => fileURLToPath(new URL(p, import.meta.url));

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    testTimeout: 30_000,
  },
  resolve: {
    alias: {
      '@factory/core': r('./packages/core'),
      '@factory/agents': r('./packages/agents'),
      '@factory/research': r('./packages/research'),
      '@factory/content': r('./packages/content'),
      '@factory/orchestrator': r('./packages/orchestrator'),
      '@factory/renderer': r('./packages/renderer'),
      '@factory/analytics': r('./packages/analytics'),
      '@factory/compliance': r('./packages/compliance'),
    },
  },
});
