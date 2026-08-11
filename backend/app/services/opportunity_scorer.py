from app.models import OfferSignals, OpportunityResult, ScoreBreakdown


WEIGHTS = {
    "demand": 0.24,
    "buyer_intent": 0.22,
    "trend": 0.14,
    "inverse_competition": 0.14,
    "commission_attractiveness": 0.16,
    "network_epc_signal": 0.10,
}


def score_opportunity(signals: OfferSignals) -> OpportunityResult:
    inverse_competition = 100 - signals.competition
    components = {
        "demand": signals.demand,
        "buyer_intent": signals.buyer_intent,
        "trend": signals.trend,
        "inverse_competition": inverse_competition,
        "commission_attractiveness": signals.commission_attractiveness,
        "network_epc_signal": signals.network_epc_signal,
    }
    score = round(sum(components[key] * WEIGHTS[key] for key in WEIGHTS), 2)
    if score >= 85:
        rating = "very_high"
    elif score >= 70:
        rating = "high"
    elif score >= 55:
        rating = "medium"
    else:
        rating = "low"

    return OpportunityResult(
        product_name=signals.product_name,
        network=signals.network,
        score=score,
        rating=rating,
        breakdown=ScoreBreakdown(**components),
    )
