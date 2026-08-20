import { ScoreBreakdownSchema, type ScoreBreakdown, type Signal } from '../core/types.ts';

/**
 * Weights come straight from the brief. They sum to 100 before penalties.
 * Saturation and risk are subtracted so a crowded or legally hazardous topic
 * cannot win on attention alone.
 */
export const SCORE_WEIGHTS = {
  attention: 25,
  growth: 20,
  commercialIntent: 20,
  monetizationPotential: 15,
  contentRepeatability: 10,
  productOpportunity: 10,
} as const;

export const PENALTY_WEIGHTS = {
  saturation: 20,
  risk: 15,
} as const;

const round = (n: number) => Number(n.toFixed(2));

export function scoreSignal(signal: Signal): ScoreBreakdown {
  const m = signal.metrics;
  const breakdown = {
    attention: round(m.attention * SCORE_WEIGHTS.attention),
    growth: round(m.growth * SCORE_WEIGHTS.growth),
    commercialIntent: round(m.commercialIntent * SCORE_WEIGHTS.commercialIntent),
    monetizationPotential: round(m.monetizationPotential * SCORE_WEIGHTS.monetizationPotential),
    contentRepeatability: round(m.contentRepeatability * SCORE_WEIGHTS.contentRepeatability),
    productOpportunity: round(m.productOpportunity * SCORE_WEIGHTS.productOpportunity),
    saturationPenalty: round(m.saturation * PENALTY_WEIGHTS.saturation),
    riskPenalty: round(m.risk * PENALTY_WEIGHTS.risk),
    total: 0,
  };

  const positive =
    breakdown.attention +
    breakdown.growth +
    breakdown.commercialIntent +
    breakdown.monetizationPotential +
    breakdown.contentRepeatability +
    breakdown.productOpportunity;

  const total = positive - breakdown.saturationPenalty - breakdown.riskPenalty;
  breakdown.total = round(Math.max(0, Math.min(100, total)));

  return ScoreBreakdownSchema.parse(breakdown);
}

/** Human-readable band used in CLI output and in the opportunity report. */
export function scoreBand(total: number): 'strong' | 'promising' | 'marginal' | 'skip' {
  if (total >= 65) return 'strong';
  if (total >= 50) return 'promising';
  if (total >= 35) return 'marginal';
  return 'skip';
}
