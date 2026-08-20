import { describe, expect, it } from 'vitest';
import { isApprovedDomain, research } from '../packages/research/research-agent.ts';
import {
  ingestAnalytics,
  revenuePer1000Views,
  runGrowthOptimizer,
} from '../packages/analytics/analytics-agent.ts';
import type { ResearchCorpus } from '../packages/research/research-agent.ts';

/* -------------------------------------------------------------------------- */
/* research                                                                    */
/* -------------------------------------------------------------------------- */

const CAPTURED = '2026-02-01T00:00:00.000Z';
const NEVER = '1970-01-01T00:00:00.000Z';

function corpus(overrides: Partial<ResearchCorpus> = {}): ResearchCorpus {
  return {
    approvedDomains: ['ftc.gov'],
    sources: [
      {
        id: 'src_ok',
        url: 'https://www.ftc.gov/guidance',
        title: 'guidance',
        publisher: 'FTC',
        capturedAt: CAPTURED,
      },
    ],
    claims: [],
    assumptions: [],
    ...overrides,
  };
}

describe('research agent evidence discipline', () => {
  it('promotes a claim to a verified fact only when its source resolves', () => {
    const bundle = research({
      brandId: 'maya',
      topic: 'disclosure rules',
      corpus: corpus({ claims: [{ statement: 'Disclosures must be hard to miss', sourceId: 'src_ok', numeric: false }] }),
    });
    const fact = bundle.facts.find((f) => f.statement.startsWith('Disclosures'));
    expect(fact?.kind).toBe('verified_fact');
    expect(fact?.sourceId).toBe('src_ok');
  });

  it('demotes a claim whose source does not exist', () => {
    const bundle = research({
      brandId: 'maya',
      topic: 'disclosure rules',
      corpus: corpus({ claims: [{ statement: 'Something asserted with no backing', sourceId: 'src_missing', numeric: false }] }),
    });
    const fact = bundle.facts.find((f) => f.statement.startsWith('Something'));
    expect(fact?.kind).toBe('assumption');
    expect(fact?.sourceId).toBeNull();
    expect(bundle.gaps.join(' ')).toMatch(/unknown sourceId/i);
  });

  it('refuses a source that is not on an approved domain', () => {
    const bundle = research({
      brandId: 'maya',
      topic: 'anything',
      corpus: corpus({
        sources: [
          {
            id: 'src_bad',
            url: 'https://random-blog.example.net/post',
            title: 'blog',
            publisher: 'blog',
            capturedAt: CAPTURED,
          },
        ],
        claims: [{ statement: 'A claim resting on an unapproved source', sourceId: 'src_bad', numeric: false }],
      }),
    });
    expect(bundle.sources.map((s) => s.id)).not.toContain('src_bad');
    expect(bundle.gaps.join(' ')).toMatch(/not on an approved domain/i);
  });

  it('will not let a never-captured source support a claim', () => {
    const bundle = research({
      brandId: 'maya',
      topic: 'anything',
      corpus: corpus({
        sources: [{ id: 'src_ok', url: 'https://www.ftc.gov/guidance', title: 't', publisher: 'FTC', capturedAt: NEVER }],
        claims: [{ statement: 'A claim citing an uncaptured source', sourceId: 'src_ok', numeric: false }],
      }),
    });
    expect(bundle.facts.find((f) => f.statement.startsWith('A claim'))?.kind).toBe('assumption');
    expect(bundle.gaps.join(' ')).toMatch(/never been captured/i);
  });

  it('records assumptions without a source id', () => {
    const bundle = research({
      brandId: 'maya',
      topic: 'anything',
      corpus: corpus({ assumptions: ['The lighting is held constant across shots'] }),
    });
    const assumption = bundle.facts.find((f) => f.statement.startsWith('The lighting'));
    expect(assumption?.kind).toBe('assumption');
    expect(assumption?.sourceId).toBeNull();
  });

  it('drops an assumption that smuggles in a number', () => {
    const bundle = research({
      brandId: 'maya',
      topic: 'anything',
      corpus: corpus({ assumptions: ['Roughly 80 percent of viewers rewatch'] }),
    });
    expect(bundle.facts.some((f) => f.statement.includes('80'))).toBe(false);
    expect(bundle.gaps.join(' ')).toMatch(/unsourced number/i);
  });

  it('flags the absence of verified facts so the script stays claim-free', () => {
    const bundle = research({ brandId: 'maya', topic: 'anything', corpus: corpus() });
    expect(bundle.gaps.join(' ')).toMatch(/no verified facts/i);
  });

  it('matches subdomains of an approved domain but not lookalikes', () => {
    expect(isApprovedDomain('https://support.google.com/x', ['google.com'])).toBe(true);
    expect(isApprovedDomain('https://ftc.gov.evil.com/x', ['ftc.gov'])).toBe(false);
  });
});

/* -------------------------------------------------------------------------- */
/* analytics + growth                                                          */
/* -------------------------------------------------------------------------- */

function row(videoId: string, revenue: number, views = 10_000, completionRate = 0.5) {
  return {
    brand: 'maya',
    platform: 'tiktok',
    videoId,
    topic: `topic ${videoId}`,
    hook: 'hook',
    views,
    watchTimeSeconds: views * 10,
    completionRate,
    revenue,
  };
}

describe('analytics', () => {
  it('computes revenue per 1000 views', () => {
    expect(revenuePer1000Views(50, 10_000)).toBe(5);
    expect(revenuePer1000Views(0, 0)).toBe(0);
  });

  it('validates ingested rows against the schema', () => {
    const records = ingestAnalytics([row('v1', 20)]);
    expect(records[0]?.revenuePer1000Views).toBe(2);
    expect(records[0]?.brand).toBe('maya');
  });

  it('derives completion rate when the export omits it', () => {
    const records = ingestAnalytics([
      { ...row('v1', 10), completionRate: undefined, watchTimeSeconds: 10_000 * 15, durationSeconds: 30 },
    ]);
    expect(records[0]?.completionRate).toBeCloseTo(0.5, 2);
  });
});

describe('growth optimizer 25/50/25 policy', () => {
  const cohort = ingestAnalytics([
    row('v1', 100),
    row('v2', 80),
    row('v3', 60),
    row('v4', 40),
    row('v5', 20),
    row('v6', 5),
    row('v7', 1),
    row('v8', 0),
  ]);

  it('splits the cohort into top 25%, middle 50%, bottom 25%', () => {
    const plan = runGrowthOptimizer('maya', cohort);
    expect(plan.scale).toHaveLength(2);
    expect(plan.iterate).toHaveLength(4);
    expect(plan.pause).toHaveLength(2);
  });

  it('scales the highest earners and pauses the lowest', () => {
    const plan = runGrowthOptimizer('maya', cohort);
    expect(plan.scale.map((r) => r.videoId)).toEqual(['v1', 'v2']);
    expect(plan.pause.map((r) => r.videoId)).toEqual(['v7', 'v8']);
  });

  it('proposes exactly 3 variations for each top performer', () => {
    const plan = runGrowthOptimizer('maya', cohort);
    for (const record of plan.scale) {
      const variations = plan.experiments.filter(
        (e) => e.variationOf === record.videoId && e.decision === 'scale',
      );
      expect(variations).toHaveLength(3);
      expect(variations.map((v) => v.variationAxis).sort()).toEqual(['cta', 'format', 'hook']);
    }
  });

  it('marks bottom-quartile videos as paused', () => {
    const plan = runGrowthOptimizer('maya', cohort);
    const paused = plan.experiments.filter((e) => e.decision === 'pause');
    expect(paused.map((e) => e.sourceVideoId).sort()).toEqual(['v7', 'v8']);
  });

  it('refuses to apply quartiles to a cohort too small to mean anything', () => {
    const plan = runGrowthOptimizer('maya', cohort.slice(0, 3));
    expect(plan.scale).toEqual([]);
    expect(plan.pause).toEqual([]);
    expect(plan.iterate).toHaveLength(3);
    expect(plan.notes.join(' ')).toMatch(/not meaningful yet/i);
  });

  it('ignores other brands', () => {
    const plan = runGrowthOptimizer('kids-learning', cohort);
    expect(plan.cohortSize).toBe(0);
  });
});
