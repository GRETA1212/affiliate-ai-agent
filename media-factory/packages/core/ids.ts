import { createHash } from 'node:crypto';

/**
 * Deterministic ids. The whole pipeline must be reproducible so that tests and
 * demo runs produce byte-identical artifacts from identical inputs.
 */
export function stableId(prefix: string, ...parts: (string | number)[]): string {
  const hash = createHash('sha256').update(parts.join('|')).digest('hex').slice(0, 10);
  return `${prefix}_${hash}`;
}

/** Seeded 32-bit PRNG (mulberry32) for deterministic mock content. */
export function seededRandom(seed: string): () => number {
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i++) {
    h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  let a = h >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Clock is injectable so runs are reproducible in tests.
 * FACTORY_FIXED_CLOCK freezes time for deterministic fixtures.
 */
export function now(): string {
  const fixed = process.env.FACTORY_FIXED_CLOCK;
  return fixed ? new Date(fixed).toISOString() : new Date().toISOString();
}
