import { describe, expect, it } from 'vitest';
import { PENALTY_WEIGHTS, SCORE_WEIGHTS, scoreBand, scoreSignal } from '../packages/agents/niche-scorer.ts';
import type { Signal } from '../packages/core/types.ts';

function signal(metrics: Partial<Signal['metrics']> = {}): Signal {
  return {
    id: 'sig_test',
    topic: 'test topic',
    niche: 'test niche',
    source: {
      id: 'src_test',
      url: 'https://example.org/evidence',
      title: 'test',
      publisher: 'test',
      capturedAt: '2026-01-01T00:00:00.000Z',
    },
    metrics: {
      attention: 0,
      growth: 0,
      commercialIntent: 0,
      monetizationPotential: 0,
      contentRepeatability: 0,
      productOpportunity: 0,
      saturation: 0,
      risk: 0,
      ...metrics,
    },
    metricBasis: 'test fixture',
  };
}

describe('niche scorer weights', () => {
  it('uses the weighting fixed by the product spec', () => {
    expect(SCORE_WEIGHTS).toEqual({
      attention: 25,
      growth: 20,
      commercialIntent: 20,
      monetizationPotential: 15,
      contentRepeatability: 10,
      productOpportunity: 10,
    });
  });

  it('positive weights sum to 100', () => {
    const total = Object.values(SCORE_WEIGHTS).reduce((sum, weight) => sum + weight, 0);
    expect(total).toBe(100);
  });

  it('scores a perfect unsaturated signal at 100', () => {
    const score = scoreSignal(
      signal({
        attention: 1,
        growth: 1,
        commercialIntent: 1,
        monetizationPotential: 1,
        contentRepeatability: 1,
        productOpportunity: 1,
      }),
    );
    expect(score.total).toBe(100);
  });

  it('scores an empty signal at 0', () => {
    expect(scoreSignal(signal()).total).toBe(0);
  });

  it('applies each weight proportionally', () => {
    const score = scoreSignal(signal({ attention: 0.5, growth: 1, productOpportunity: 0.25 }));
    expect(score.attention).toBe(12.5);
    expect(score.growth).toBe(20);
    expect(score.productOpportunity).toBe(2.5);
    expect(score.total).toBe(35);
  });

  it('subtracts saturation and risk penalties', () => {
    const score = scoreSignal(signal({ attention: 1, saturation: 1, risk: 1 }));
    expect(score.saturationPenalty).toBe(PENALTY_WEIGHTS.saturation);
    expect(score.riskPenalty).toBe(PENALTY_WEIGHTS.risk);
    // 25 attention - 20 saturation - 15 risk would be negative, so it clamps.
    expect(score.total).toBe(0);
  });

  it('never returns a negative total, so ranking stays meaningful', () => {
    const score = scoreSignal(signal({ saturation: 1, risk: 1 }));
    expect(score.total).toBeGreaterThanOrEqual(0);
  });

  it('penalises a saturated topic below an equivalent uncrowded one', () => {
    const base = { attention: 0.8, growth: 0.8, commercialIntent: 0.8 };
    const clean = scoreSignal(signal(base));
    const crowded = scoreSignal(signal({ ...base, saturation: 0.9 }));
    expect(crowded.total).toBeLessThan(clean.total);
  });

  it('is deterministic', () => {
    const input = signal({ attention: 0.63, growth: 0.41 });
    expect(scoreSignal(input)).toEqual(scoreSignal(input));
  });

  it('bands scores for human reading', () => {
    expect(scoreBand(80)).toBe('strong');
    expect(scoreBand(55)).toBe('promising');
    expect(scoreBand(40)).toBe('marginal');
    expect(scoreBand(10)).toBe('skip');
  });
});
