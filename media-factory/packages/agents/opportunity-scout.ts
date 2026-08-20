import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { z } from 'zod';
import { brandsDir } from '../core/brand.ts';
import { now, stableId } from '../core/ids.ts';
import { SignalSchema, type Brand, type Opportunity, OpportunitySchema, type Signal } from '../core/types.ts';
import { scoreSignal } from './niche-scorer.ts';

const SignalFileSchema = z.object({
  _README: z.union([z.string(), z.array(z.string())]).optional(),
  signals: z.array(SignalSchema),
});

/**
 * Repository template evidence. The reserved `.invalid` TLD can never resolve,
 * so an unreplaced placeholder is impossible to mistake for observed data.
 */
export function isPlaceholderSource(url: string): boolean {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return host.endsWith('.invalid') || host === 'example.com' || host.endsWith('.example.com');
  } catch {
    return true;
  }
}

const NEVER_CAPTURED = '1970-01-01T00:00:00.000Z';

/** Loose niche match: a signal niche need only overlap the requested niche. */
function nicheMatches(signalNiche: string, requested: string): boolean {
  const a = signalNiche.toLowerCase();
  const b = requested.toLowerCase();
  if (a === b || a.includes(b) || b.includes(a)) return true;
  const terms = a.split(/[^a-z0-9]+/).filter((t) => t.length > 2);
  return terms.some((t) => b.includes(t));
}

export interface ScoutResult {
  opportunities: Opportunity[];
  /** Signals dropped for missing or malformed evidence, with the reason. */
  rejected: { id: string; reason: string }[];
  /** Loud warnings: unreplaced template evidence, uncaptured sources. */
  warnings: string[];
  /** True when every surviving opportunity rests on template evidence. */
  placeholderEvidenceOnly: boolean;
  /** Present when no evidence exists at all. The scout returns nothing rather
   *  than inventing a trend to fill the gap. */
  notice: string | null;
}

export interface ScoutOptions {
  brand: Brand;
  /** Optional niche override; defaults to the brand's own niche. */
  niche?: string;
  limit?: number;
  /** Restrict to signals whose topic contains this string. */
  topic?: string;
  /** Injected for tests. Defaults to the brand's signals.json. */
  signals?: Signal[];
  dir?: string;
}

/**
 * Reads observed signals and ranks them. It has exactly one hard rule:
 * a signal without a resolvable source URL and capture timestamp cannot
 * become an opportunity. There is no code path that fabricates metrics.
 */
export function scout(options: ScoutOptions): ScoutResult {
  const { brand, limit = 5 } = options;
  const niche = options.niche ?? brand.niche;
  const raw = options.signals ?? loadSignals(brand.id, options.dir);
  const rejected: ScoutResult['rejected'] = [];

  if (raw.length === 0) {
    return {
      opportunities: [],
      rejected,
      warnings: [],
      placeholderEvidenceOnly: false,
      notice:
        `No signals available for brand "${brand.id}". The scout does not generate trend data. ` +
        `Add captured evidence to brands/${brand.id}/signals.json or connect a research source, then re-run.`,
    };
  }

  const scored: Opportunity[] = [];
  for (const signal of raw) {
    const parsed = SignalSchema.safeParse(signal);
    if (!parsed.success) {
      rejected.push({ id: (signal as Signal)?.id ?? 'unknown', reason: parsed.error.issues[0]?.message ?? 'invalid signal' });
      continue;
    }
    const value = parsed.data;
    if (!value.source?.url || !value.source.capturedAt) {
      rejected.push({ id: value.id, reason: 'missing source url or capturedAt - evidence is mandatory' });
      continue;
    }
    if (niche && !nicheMatches(value.niche, niche)) {
      rejected.push({ id: value.id, reason: `niche mismatch (signal: ${value.niche})` });
      continue;
    }
    if (options.topic && !value.topic.toLowerCase().includes(options.topic.toLowerCase())) {
      rejected.push({ id: value.id, reason: `topic filter did not match (signal: ${value.topic})` });
      continue;
    }

    const score = scoreSignal(value);
    scored.push(
      OpportunitySchema.parse({
        id: stableId('opp', brand.id, value.id),
        brandId: brand.id,
        topic: value.topic,
        niche: value.niche,
        score,
        evidence: [value.source],
        metricBasis: value.metricBasis,
        createdAt: now(),
      }),
    );
  }

  scored.sort((a, b) => b.score.total - a.score.total || a.topic.localeCompare(b.topic));

  // Evidence quality is reported, never silently tolerated.
  const warnings: string[] = [];
  const placeholders = scored.filter((o) => o.evidence.some((e) => isPlaceholderSource(e.url)));
  if (placeholders.length > 0) {
    warnings.push(
      `${placeholders.length} of ${scored.length} opportunities still rest on PLACEHOLDER template evidence. ` +
        `These rank template values, not observed trends. Replace them in brands/${brand.id}/signals.json.`,
    );
  }
  for (const opportunity of scored) {
    for (const source of opportunity.evidence) {
      if (source.capturedAt === NEVER_CAPTURED) {
        warnings.push(`opportunity "${opportunity.topic}" cites a source that has never been captured.`);
      }
    }
  }

  return {
    opportunities: scored.slice(0, limit),
    rejected,
    warnings,
    placeholderEvidenceOnly: scored.length > 0 && placeholders.length === scored.length,
    notice: scored.length === 0 ? 'Every signal was rejected. See `rejected` for reasons.' : null,
  };
}

export function loadSignals(brandId: string, dir = brandsDir()): Signal[] {
  const file = join(dir, brandId, 'signals.json');
  if (!existsSync(file)) return [];
  const parsed = SignalFileSchema.safeParse(JSON.parse(readFileSync(file, 'utf8')));
  if (!parsed.success) {
    throw new Error(`signals file for "${brandId}" is invalid: ${parsed.error.message}`);
  }
  return parsed.data.signals;
}
