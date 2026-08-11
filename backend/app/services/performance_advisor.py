from datetime import UTC, datetime
from statistics import median
from typing import Literal

from pydantic import BaseModel, Field

from app.services import campaign_workspace as workspace

Classification = Literal[
    "winner",
    "loser",
    "promising",
    "neutral",
    "insufficient_data",
    "inactive",
]
RecommendedAction = Literal[
    "scale",
    "increase_test",
    "hold",
    "optimize",
    "pause_or_rework",
    "collect_data",
    "none",
]


class AdvisorSettings(BaseModel):
    min_sample_clicks: int = Field(default=50, ge=10, le=10000)
    stop_clicks: int = Field(default=150, ge=25, le=50000)
    low_conversion_rate: float = Field(default=0.005, ge=0, le=1)
    healthy_conversion_rate: float = Field(default=0.02, ge=0, le=1)
    winner_epc_multiplier: float = Field(default=1.25, ge=1, le=10)
    loser_epc_multiplier: float = Field(default=0.5, ge=0, le=1)


class CurrencyLeader(BaseModel):
    currency: str
    campaign_id: str
    campaign_name: str
    epc: float


class CampaignRecommendation(BaseModel):
    campaign_id: str
    campaign_name: str
    product_name: str
    campaign_status: workspace.CampaignStatus
    classification: Classification
    recommended_action: RecommendedAction
    priority: int = Field(ge=0, le=5)
    confidence: float = Field(ge=0, le=1)
    human_clicks: int
    approved_conversions: int
    pending_conversions: int
    conversion_rate: float
    approved_revenue_by_currency: dict[str, float]
    epc_by_currency: dict[str, float]
    peer_median_epc_by_currency: dict[str, float]
    reasons: list[str]
    next_actions: list[str]


class AdvisorSummary(BaseModel):
    total_campaigns: int
    winners: int
    losers: int
    promising: int
    insufficient_data: int
    action_required: int
    leaders_by_currency: list[CurrencyLeader]


class AdvisorResponse(BaseModel):
    generated_at: str
    settings: AdvisorSettings
    summary: AdvisorSummary
    recommendations: list[CampaignRecommendation]
    methodology_note: str


def analyze_portfolio(settings: AdvisorSettings | None = None) -> AdvisorResponse:
    resolved = settings or AdvisorSettings()
    if resolved.stop_clicks < resolved.min_sample_clicks:
        resolved = resolved.model_copy(update={"stop_clicks": resolved.min_sample_clicks})

    campaigns = workspace.list_campaigns()
    peer_medians = _peer_medians(campaigns, resolved.min_sample_clicks)
    recommendations = [_recommend(detail, resolved, peer_medians) for detail in campaigns]
    recommendations.sort(
        key=lambda item: (
            item.priority,
            item.confidence,
            item.human_clicks,
            item.approved_conversions,
        ),
        reverse=True,
    )

    leaders = _currency_leaders(campaigns, resolved.min_sample_clicks)
    summary = AdvisorSummary(
        total_campaigns=len(recommendations),
        winners=sum(item.classification == "winner" for item in recommendations),
        losers=sum(item.classification == "loser" for item in recommendations),
        promising=sum(item.classification == "promising" for item in recommendations),
        insufficient_data=sum(
            item.classification == "insufficient_data" for item in recommendations
        ),
        action_required=sum(
            item.recommended_action in {"scale", "increase_test", "optimize", "pause_or_rework"}
            for item in recommendations
        ),
        leaders_by_currency=leaders,
    )
    return AdvisorResponse(
        generated_at=datetime.now(UTC).isoformat(),
        settings=resolved,
        summary=summary,
        recommendations=recommendations,
        methodology_note=(
            "Recommendations use only this workspace's observed human clicks, approved/pending "
            "conversions, conversion rate and real EPC. EPC comparisons are made only within the "
            "same currency. The advisor never treats network-average EPC or opportunity scores as "
            "proof of profit, and it waits for a minimum sample before strong winner/loser calls."
        ),
    )


def _peer_medians(
    campaigns: list[workspace.CampaignDetail],
    min_sample_clicks: int,
) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for detail in campaigns:
        metrics = detail.metrics
        if metrics.human_clicks < min_sample_clicks or metrics.approved_conversions == 0:
            continue
        for currency, epc in metrics.epc_by_currency.items():
            if epc > 0:
                values.setdefault(currency, []).append(float(epc))
    return {
        currency: round(float(median(epcs)), 6)
        for currency, epcs in values.items()
        if epcs
    }


def _currency_leaders(
    campaigns: list[workspace.CampaignDetail],
    min_sample_clicks: int,
) -> list[CurrencyLeader]:
    leaders: dict[str, CurrencyLeader] = {}
    for detail in campaigns:
        if detail.metrics.human_clicks < min_sample_clicks:
            continue
        for currency, epc in detail.metrics.epc_by_currency.items():
            if epc <= 0:
                continue
            current = leaders.get(currency)
            if current is None or epc > current.epc:
                leaders[currency] = CurrencyLeader(
                    currency=currency,
                    campaign_id=detail.campaign.id,
                    campaign_name=detail.campaign.name,
                    epc=round(epc, 6),
                )
    return sorted(leaders.values(), key=lambda item: item.currency)


def _recommend(
    detail: workspace.CampaignDetail,
    settings: AdvisorSettings,
    peer_medians: dict[str, float],
) -> CampaignRecommendation:
    campaign = detail.campaign
    metrics = detail.metrics
    clicks = metrics.human_clicks
    approved = metrics.approved_conversions
    pending = metrics.pending_conversions
    confidence = _confidence(clicks, approved, settings)
    peer_epc = {
        currency: peer_medians[currency]
        for currency in metrics.epc_by_currency
        if currency in peer_medians
    }
    ratios = [
        metrics.epc_by_currency[currency] / benchmark
        for currency, benchmark in peer_epc.items()
        if benchmark > 0
    ]

    if campaign.status == "archived":
        return _result(
            detail,
            "inactive",
            "none",
            priority=0,
            confidence=1.0,
            peer_epc=peer_epc,
            reasons=["Campaign is archived, so no active optimization decision is needed."],
            next_actions=["Keep historical data for comparison; create a new campaign to retest."],
        )

    if clicks < settings.min_sample_clicks:
        remaining = settings.min_sample_clicks - clicks
        return _result(
            detail,
            "insufficient_data",
            "collect_data",
            priority=1,
            confidence=min(confidence, 0.49),
            peer_epc=peer_epc,
            reasons=[
                (
                    f"Only {clicks} human clicks are recorded; the minimum sample is "
                    f"{settings.min_sample_clicks}."
                ),
                "Calling a winner or loser this early would be unstable.",
            ],
            next_actions=[
                f"Collect at least {remaining} more qualified human clicks.",
                "Keep the offer and primary CTA stable while building the sample.",
                "Track source/content parameters so later EPC can be segmented.",
            ],
        )

    if approved == 0 and pending > 0:
        return _result(
            detail,
            "neutral",
            "hold",
            priority=2,
            confidence=confidence,
            peer_epc=peer_epc,
            reasons=[
                f"There are {pending} pending network conversions and no approved conversions yet.",
                "A strong stop/scale decision should wait for the network to validate them.",
            ],
            next_actions=[
                "Wait for pending conversions to approve or reverse.",
                "Run network sync again before changing the offer.",
            ],
        )

    if approved == 0 and clicks >= settings.stop_clicks:
        return _result(
            detail,
            "loser",
            "pause_or_rework",
            priority=5,
            confidence=max(confidence, 0.8),
            peer_epc=peer_epc,
            reasons=[
                f"{clicks} qualified human clicks produced no approved conversion.",
                f"The stop threshold is {settings.stop_clicks} clicks.",
            ],
            next_actions=[
                "Pause new promotion until the affiliate link and attribution are verified.",
                "Check that the offer matches the visitor's buyer intent and geography.",
                "Replace the offer or rewrite the content/CTA before restarting traffic.",
            ],
        )

    if approved == 0:
        return _result(
            detail,
            "neutral",
            "optimize",
            priority=3,
            confidence=confidence,
            peer_epc=peer_epc,
            reasons=[
                f"The campaign has reached {clicks} clicks without an approved conversion.",
                "The sample is meaningful, but it has not reached the hard stop threshold yet.",
            ],
            next_actions=[
                "Verify the affiliate link and network attribution first.",
                "Improve the CTA and buyer-intent match without changing several variables at once.",
                f"Re-evaluate by {settings.stop_clicks} human clicks.",
            ],
        )

    if ratios and max(ratios) >= settings.winner_epc_multiplier and approved >= 2:
        best_ratio = max(ratios)
        return _result(
            detail,
            "winner",
            "scale",
            priority=5,
            confidence=confidence,
            peer_epc=peer_epc,
            reasons=[
                f"Real EPC is {best_ratio:.2f}× the same-currency peer median.",
                f"The campaign has {approved} approved conversions from {clicks} human clicks.",
            ],
            next_actions=[
                "Increase qualified traffic gradually instead of making a large jump at once.",
                "Create 2-3 new content variations around the same buyer intent and offer.",
                "Re-check EPC after the next 100 human clicks to confirm the advantage holds.",
            ],
        )

    if (
        ratios
        and min(ratios) <= settings.loser_epc_multiplier
        and clicks >= settings.stop_clicks
    ):
        worst_ratio = min(ratios)
        return _result(
            detail,
            "loser",
            "optimize",
            priority=4,
            confidence=confidence,
            peer_epc=peer_epc,
            reasons=[
                f"Real EPC is only {worst_ratio:.2f}× the same-currency peer median.",
                f"The campaign has enough traffic for a stronger comparison ({clicks} clicks).",
            ],
            next_actions=[
                "Do not scale this campaign while stronger same-currency alternatives exist.",
                "Test a tighter buyer-intent angle or a different offer.",
                "Keep one control version so the next test has a clean comparison.",
            ],
        )

    if metrics.conversion_rate >= settings.healthy_conversion_rate and approved >= 2:
        return _result(
            detail,
            "promising",
            "increase_test",
            priority=4,
            confidence=confidence,
            peer_epc=peer_epc,
            reasons=[
                (
                    f"Conversion rate is {metrics.conversion_rate * 100:.2f}%, at or above the "
                    f"{settings.healthy_conversion_rate * 100:.2f}% healthy-test threshold."
                ),
                (
                    f"There are {approved} approved conversions, so the signal is repeatable "
                    "enough for a larger test."
                ),
            ],
            next_actions=[
                "Send another 50-100 qualified clicks before calling it a durable winner.",
                "Test one additional content angle while keeping the offer constant.",
                "Promote to winner only if EPC remains strong as the sample grows.",
            ],
        )

    if (
        metrics.conversion_rate < settings.low_conversion_rate
        and clicks >= settings.stop_clicks
    ):
        return _result(
            detail,
            "loser",
            "optimize",
            priority=4,
            confidence=confidence,
            peer_epc=peer_epc,
            reasons=[
                (
                    f"Conversion rate is {metrics.conversion_rate * 100:.2f}%, below the "
                    f"{settings.low_conversion_rate * 100:.2f}% low-performance threshold."
                ),
                f"The campaign has {clicks} human clicks, enough for a meaningful warning.",
            ],
            next_actions=[
                "Audit content-to-offer fit and the CTA before buying or sending more traffic.",
                "Compare the landing page, geography and device mix for friction.",
                "Consider replacing the offer if the next controlled test does not improve CVR.",
            ],
        )

    return _result(
        detail,
        "neutral",
        "hold",
        priority=2,
        confidence=confidence,
        peer_epc=peer_epc,
        reasons=[
            "The campaign has enough data to monitor but does not yet meet winner or loser rules.",
            f"Current conversion rate is {metrics.conversion_rate * 100:.2f}%.",
        ],
        next_actions=[
            "Keep collecting qualified traffic without making a major budget change.",
            "Use source/content tags to find which traffic segments contribute the best EPC.",
        ],
    )


def _result(
    detail: workspace.CampaignDetail,
    classification: Classification,
    recommended_action: RecommendedAction,
    *,
    priority: int,
    confidence: float,
    peer_epc: dict[str, float],
    reasons: list[str],
    next_actions: list[str],
) -> CampaignRecommendation:
    return CampaignRecommendation(
        campaign_id=detail.campaign.id,
        campaign_name=detail.campaign.name,
        product_name=detail.campaign.product_name,
        campaign_status=detail.campaign.status,
        classification=classification,
        recommended_action=recommended_action,
        priority=priority,
        confidence=round(confidence, 3),
        human_clicks=detail.metrics.human_clicks,
        approved_conversions=detail.metrics.approved_conversions,
        pending_conversions=detail.metrics.pending_conversions,
        conversion_rate=detail.metrics.conversion_rate,
        approved_revenue_by_currency=detail.metrics.approved_revenue_by_currency,
        epc_by_currency=detail.metrics.epc_by_currency,
        peer_median_epc_by_currency=peer_epc,
        reasons=reasons,
        next_actions=next_actions,
    )


def _confidence(clicks: int, conversions: int, settings: AdvisorSettings) -> float:
    click_component = min(clicks / max(settings.stop_clicks, 1), 1.0)
    conversion_component = min(conversions / 5, 1.0)
    return min(0.98, 0.35 + (0.4 * click_component) + (0.23 * conversion_component))
