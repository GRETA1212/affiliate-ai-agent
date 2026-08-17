from __future__ import annotations

from .models import AffiliateProgram, ScoreBreakdown

VERIFICATION_MULTIPLIERS = {
    "verified": 1.0,
    "unverified": 0.72,
    "stale": 0.55,
    "rejected": 0.0,
}


def _economics_score(program: AffiliateProgram) -> float:
    price = program.monthly_price_from or 0.0
    rate = (program.commission_rate_pct or 0.0) / 100.0
    recurring_horizon = 24 if program.lifetime_recurring else (program.recurring_months or 1)
    recurring_value = price * rate * recurring_horizon
    fixed_value = program.commission_amount or 0.0
    expected_value = max(recurring_value, fixed_value)
    return min(expected_value / 500.0, 1.0)


def score_program(program: AffiliateProgram) -> ScoreBreakdown:
    program.validate()
    economics = _economics_score(program)
    attribution = min((program.cookie_days or 0) / 120.0, 1.0)
    fit = program.niche_fit
    conversion = program.conversion_confidence
    competition = 1.0 - program.competition_penalty
    friction = 1.0 - program.approval_friction
    verification_multiplier = VERIFICATION_MULTIPLIERS[program.verification_status]

    weighted = (
        economics * 0.30
        + attribution * 0.15
        + fit * 0.20
        + conversion * 0.15
        + competition * 0.10
        + friction * 0.10
    )
    total = round(weighted * verification_multiplier * 100.0, 2)
    return ScoreBreakdown(
        total=total,
        economics=round(economics * 100.0, 2),
        attribution=round(attribution * 100.0, 2),
        fit=round(fit * 100.0, 2),
        conversion=round(conversion * 100.0, 2),
        competition=round(competition * 100.0, 2),
        friction=round(friction * 100.0, 2),
        verification_multiplier=verification_multiplier,
    )
