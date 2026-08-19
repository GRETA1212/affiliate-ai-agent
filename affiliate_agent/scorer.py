from __future__ import annotations

from .models import Opportunity


WEIGHTS = {
    "demand": 0.30,
    "commission": 0.20,
    "conversion_potential": 0.15,
    "content_potential": 0.15,
    "low_competition": 0.10,
    "recurring_revenue": 0.10,
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def commission_score(opportunity: Opportunity) -> float:
    """Normalize commission attractiveness to a 0-100 score.

    Uses both commission percentage and absolute payout. This keeps a low-price
    physical product from outranking a higher-value software offer solely on rate.
    """
    estimated_payout = opportunity.price * opportunity.commission_rate
    rate_component = _clamp(opportunity.commission_rate * 100.0)
    payout_component = _clamp((estimated_payout / 50.0) * 100.0)
    return 0.45 * rate_component + 0.55 * payout_component


def score_opportunity(opportunity: Opportunity) -> float:
    score = (
        WEIGHTS["demand"] * _clamp(opportunity.demand)
        + WEIGHTS["commission"] * commission_score(opportunity)
        + WEIGHTS["conversion_potential"] * _clamp(opportunity.conversion_potential)
        + WEIGHTS["content_potential"] * _clamp(opportunity.content_potential)
        + WEIGHTS["low_competition"] * (100.0 - _clamp(opportunity.competition))
        + WEIGHTS["recurring_revenue"] * _clamp(opportunity.recurring_revenue)
    )
    return round(score, 2)
