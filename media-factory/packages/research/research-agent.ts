import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { z } from 'zod';
import { brandsDir } from '../core/brand.ts';
import { now, stableId } from '../core/ids.ts';
import {
  FactSchema,
  ResearchBundleSchema,
  ResearchSourceSchema,
  type Fact,
  type ResearchBundle,
  type ResearchSource,
} from '../core/types.ts';

const CorpusSchema = z.object({
  _README: z.union([z.string(), z.array(z.string())]).optional(),
  /** Only sources on these domains may be cited. */
  approvedDomains: z.array(z.string()).default([]),
  sources: z.array(ResearchSourceSchema).default([]),
  claims: z
    .array(
      z.object({
        statement: z.string().min(8),
        sourceId: z.string(),
        numeric: z.boolean().default(false),
      }),
    )
    .default([]),
  /** Framing statements. Never cited, never allowed to carry numbers. */
  assumptions: z.array(z.string()).default([]),
});

const NEVER_CAPTURED = '1970-01-01T00:00:00.000Z';

export function isApprovedDomain(url: string, approvedDomains: string[]): boolean {
  if (approvedDomains.length === 0) return true;
  try {
    const host = new URL(url).hostname.toLowerCase();
    return approvedDomains.some((d) => host === d.toLowerCase() || host.endsWith(`.${d.toLowerCase()}`));
  } catch {
    return false;
  }
}
export type ResearchCorpus = z.infer<typeof CorpusSchema>;

export interface ResearchOptions {
  brandId: string;
  topic: string;
  /** Extra evidence carried over from the scout, e.g. the opportunity source. */
  extraSources?: ResearchSource[];
  corpus?: ResearchCorpus;
  dir?: string;
}

const STOPWORDS = new Set([
  'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'with', 'my',
  'your', 'it', 'is', 'are', 'how', 'why', 'what', 'ai',
]);

/**
 * The research step has one job worth trusting: keep the line between what a
 * source says and what we are assuming. A claim without a resolvable source id
 * is downgraded to an assumption, and the QA agent refuses to let an assumption
 * carry a number.
 */
export function research(options: ResearchOptions): ResearchBundle {
  const corpus = options.corpus ?? loadCorpus(options.brandId, options.dir);
  const gapsFromSources: string[] = [];

  // A source is only citable if it sits on an approved domain AND has actually
  // been captured. Both checks happen before any claim can resolve against it.
  const citableSources = corpus.sources.filter((source) => {
    if (!isApprovedDomain(source.url, corpus.approvedDomains)) {
      gapsFromSources.push(`source "${source.id}" refused: ${source.url} is not on an approved domain`);
      return false;
    }
    if (source.capturedAt === NEVER_CAPTURED) {
      gapsFromSources.push(`source "${source.id}" is registered but has never been captured, so it cannot support a claim`);
      return false;
    }
    return true;
  });
  const sourceIndex = new Map(citableSources.map((s) => [s.id, s]));
  const topicTerms = tokenize(options.topic);

  const scoredClaims = corpus.claims
    .map((claim) => ({ claim, overlap: overlapScore(topicTerms, tokenize(claim.statement)) }))
    .sort((a, b) => b.overlap - a.overlap);

  const relevant = scoredClaims.filter((entry) => entry.overlap > 0);
  const selected = (relevant.length > 0 ? relevant : scoredClaims).slice(0, 4);

  const facts: Fact[] = [];
  const gaps: string[] = [...gapsFromSources];
  const usedSources = new Map<string, ResearchSource>();

  for (const { claim } of selected) {
    const source = sourceIndex.get(claim.sourceId);
    if (!source) {
      // Unresolvable source: keep the statement but strip its authority.
      facts.push(
        FactSchema.parse({
          id: stableId('fact', options.topic, claim.statement),
          statement: claim.statement,
          kind: 'assumption',
          sourceId: null,
          numeric: claim.numeric,
        }),
      );
      gaps.push(`claim has an unknown sourceId "${claim.sourceId}" and was demoted to an assumption`);
      continue;
    }
    usedSources.set(source.id, source);
    facts.push(
      FactSchema.parse({
        id: stableId('fact', options.topic, claim.statement),
        statement: claim.statement,
        kind: 'verified_fact',
        sourceId: source.id,
        numeric: claim.numeric,
      }),
    );
  }

  // Declared assumptions enter as assumptions, never as facts, and may not
  // carry a number - an unsourced number is the exact failure mode QA blocks.
  for (const assumption of corpus.assumptions) {
    if (/\d/.test(assumption)) {
      gaps.push(`assumption dropped for carrying an unsourced number: "${assumption}"`);
      continue;
    }
    facts.push(
      FactSchema.parse({
        id: stableId('assumption', options.brandId, assumption),
        statement: assumption,
        kind: 'assumption',
        sourceId: null,
        numeric: false,
      }),
    );
  }

  for (const source of options.extraSources ?? []) usedSources.set(source.id, source);

  if (relevant.length === 0 && corpus.claims.length > 0) {
    gaps.push(
      `no source in the corpus mentions "${options.topic}" directly; the strongest available claims were used and should be re-checked before publishing`,
    );
  }
  if (facts.filter((f) => f.kind === 'verified_fact').length === 0) {
    gaps.push('no verified facts available - the script must avoid numeric and factual claims entirely');
  }

  return ResearchBundleSchema.parse({
    id: stableId('res', options.brandId, options.topic),
    topic: options.topic,
    sources: [...usedSources.values()],
    facts,
    gaps,
    createdAt: now(),
  });
}

export function loadCorpus(brandId: string, dir = brandsDir()): ResearchCorpus {
  const file = join(dir, brandId, 'research.json');
  if (!existsSync(file)) return { approvedDomains: [], sources: [], claims: [], assumptions: [] };
  const parsed = CorpusSchema.safeParse(JSON.parse(readFileSync(file, 'utf8')));
  if (!parsed.success) throw new Error(`research corpus for "${brandId}" is invalid: ${parsed.error.message}`);
  return parsed.data;
}

function tokenize(value: string): Set<string> {
  return new Set(
    value
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, ' ')
      .split(/\s+/)
      .filter((word) => word.length > 2 && !STOPWORDS.has(word)),
  );
}

function overlapScore(a: Set<string>, b: Set<string>): number {
  let hits = 0;
  for (const term of a) if (b.has(term)) hits++;
  return hits;
}
