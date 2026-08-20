import { now, stableId } from '../core/ids.ts';
import {
  AnalyticsRecordSchema,
  ExperimentSchema,
  type AnalyticsRecord,
  type Experiment,
} from '../core/types.ts';

/**
 * AnalyticsAgent + GrowthOptimizer.
 *
 * The analytics schema is the contract for whatever you paste in from platform
 * exports. Nothing here fetches metrics: platform analytics come from the
 * creator's own dashboards or official APIs, and inventing engagement numbers
 * would poison every downstream decision.
 */

export interface RawAnalyticsRow {
  brand: string;
  platform: string;
  videoId: string;
  topic: string;
  hook: string;
  views: number;
  watchTimeSeconds: number;
  completionRate?: number;
  profileVisits?: number;
  clicks?: number;
  orders?: number;
  revenue?: number;
  durationSeconds?: number;
  recordedAt?: string;
}

/** revenue per 1000 views - the metric the optimizer ranks on. */
export function revenuePer1000Views(revenue: number, views: number): number {
  if (views <= 0) return 0;
  return Number(((revenue / views) * 1000).toFixed(4));
}

export function ingestAnalytics(rows: RawAnalyticsRow[]): AnalyticsRecord[] {
  return rows.map((row) => {
    // Completion rate is derived when the platform export omits it.
    const completionRate =
      row.completionRate ??
      (row.durationSeconds && row.views > 0
        ? Math.min(1, row.watchTimeSeconds / row.views / row.durationSeconds)
        : 0);

    return AnalyticsRecordSchema.parse({
      id: stableId('analytics', row.brand, row.platform, row.videoId),
      brand: row.brand,
      platform: row.platform,
      videoId: row.videoId,
      topic: row.topic,
      hook: row.hook,
      views: Math.round(row.views),
      watchTimeSeconds: row.watchTimeSeconds,
      completionRate: Number(Math.min(1, Math.max(0, completionRate)).toFixed(4)),
      profileVisits: Math.round(row.profileVisits ?? 0),
      clicks: Math.round(row.clicks ?? 0),
      orders: Math.round(row.orders ?? 0),
      revenue: row.revenue ?? 0,
      revenuePer1000Views: revenuePer1000Views(row.revenue ?? 0, row.views),
      recordedAt: row.recordedAt ?? now(),
    });
  });
}

/* -------------------------------------------------------------------------- */
/* GrowthOptimizer                                                             */
/* -------------------------------------------------------------------------- */

/**
 * Ranking metric. Revenue per 1000 views leads because it is the only number
 * that connects a video to the business. Completion rate breaks ties, since a
 * video with no revenue attached yet is still telling you whether it held
 * attention.
 */
export function performanceScore(record: AnalyticsRecord): number {
  return record.revenuePer1000Views * 1000 + record.completionRate;
}

export interface OptimizerPlan {
  brand: string;
  cohortSize: number;
  scale: AnalyticsRecord[];
  iterate: AnalyticsRecord[];
  pause: AnalyticsRecord[];
  experiments: Experiment[];
  notes: string[];
}

const VARIATION_AXES = ['hook', 'format', 'cta'] as const;

/**
 * Policy from the spec:
 *   top 25%    -> create 3 variations
 *   middle 50% -> keep testing
 *   bottom 25% -> pause
 */
export function runGrowthOptimizer(brand: string, records: AnalyticsRecord[]): OptimizerPlan {
  const notes: string[] = [];
  const cohort = records
    .filter((r) => r.brand === brand)
    .sort((a, b) => performanceScore(b) - performanceScore(a) || a.videoId.localeCompare(b.videoId));

  if (cohort.length === 0) {
    return { brand, cohortSize: 0, scale: [], iterate: [], pause: [], experiments: [], notes: ['no analytics recorded for this brand'] };
  }
  if (cohort.length < 4) {
    notes.push(
      `only ${cohort.length} videos in the cohort - quartiles are not meaningful yet. Everything is treated as "iterate" until there are at least 4.`,
    );
    return { brand, cohortSize: cohort.length, scale: [], iterate: cohort, pause: [], experiments: [], notes };
  }

  const topCount = Math.max(1, Math.floor(cohort.length * 0.25));
  const bottomCount = Math.max(1, Math.floor(cohort.length * 0.25));

  const scale = cohort.slice(0, topCount);
  const pause = cohort.slice(cohort.length - bottomCount);
  const iterate = cohort.slice(topCount, cohort.length - bottomCount);

  const experiments: Experiment[] = [];

  // Top quartile: three variations each, one per axis, so the winning idea is
  // tested rather than merely repeated.
  for (const record of scale) {
    for (const axis of VARIATION_AXES) {
      experiments.push(
        ExperimentSchema.parse({
          id: stableId('experiment', record.videoId, axis),
          brand,
          sourceVideoId: record.videoId,
          topic: record.topic,
          decision: 'scale',
          variationOf: record.videoId,
          variationAxis: axis,
          hypothesis: `"${record.topic}" performed in the top quartile. Changing the ${axis} while holding the rest constant should isolate how much of that came from the ${axis}.`,
          status: 'proposed',
          createdAt: now(),
        }),
      );
    }
  }

  for (const record of iterate) {
    experiments.push(
      ExperimentSchema.parse({
        id: stableId('experiment', record.videoId, 'iterate'),
        brand,
        sourceVideoId: record.videoId,
        topic: record.topic,
        decision: 'iterate',
        variationOf: null,
        variationAxis: 'none',
        hypothesis: 'Mid-cohort performance. Keep running as-is to gather more data before changing anything.',
        status: 'proposed',
        createdAt: now(),
      }),
    );
  }

  for (const record of pause) {
    experiments.push(
      ExperimentSchema.parse({
        id: stableId('experiment', record.videoId, 'pause'),
        brand,
        sourceVideoId: record.videoId,
        topic: record.topic,
        decision: 'pause',
        variationOf: null,
        variationAxis: 'none',
        hypothesis: 'Bottom quartile. Pause this topic and reallocate to higher-performing angles.',
        status: 'proposed',
        createdAt: now(),
      }),
    );
  }

  notes.push(`cohort of ${cohort.length}: ${scale.length} scale, ${iterate.length} iterate, ${pause.length} pause`);

  return { brand, cohortSize: cohort.length, scale, iterate, pause, experiments, notes };
}
