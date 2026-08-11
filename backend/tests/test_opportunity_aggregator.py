from app.connectors.direct_program import DirectProgramScan
from app.services import opportunity_aggregator
from app.services.opportunity_aggregator import TopOpportunityRequest, find_top_opportunities


def test_top_opportunities_rank_direct_program(monkeypatch) -> None:
    monkeypatch.setattr(opportunity_aggregator.cj, "status", lambda: _status(False))
    monkeypatch.setattr(opportunity_aggregator.impact, "status", lambda: _status(False))
    monkeypatch.setattr(opportunity_aggregator.youtube, "status", lambda: _status(False))
    monkeypatch.setattr(
        opportunity_aggregator,
        "scan_program",
        lambda request: DirectProgramScan(
            url=str(request.url),
            final_url=str(request.url),
            title="Acme AI Affiliate Program",
            commission_percent=40.0,
            commission_text="Earn 40% commission on eligible subscriptions.",
            cookie_days=90,
            recurring=True,
            network_hint="impact",
            application_url="https://acme.example/apply",
            evidence=["40% commission", "90-day cookie", "Recurring commission language detected"],
            confidence=0.9,
        ),
    )

    response = find_top_opportunities(
        TopOpportunityRequest(
            keywords="AI",
            direct_urls=["https://acme.example/affiliates"],
            include_cj=True,
            include_impact=True,
            include_verified_catalog=False,
            include_youtube=False,
        )
    )

    assert len(response.opportunities) == 1
    item = response.opportunities[0]
    assert item.source == "direct"
    assert item.commercial_readiness_score > 70
    assert item.opportunity_score == item.commercial_readiness_score
    assert item.recurring is True
    assert len(response.warnings) == 2


def test_verified_catalog_works_without_network_credentials(monkeypatch) -> None:
    monkeypatch.setattr(opportunity_aggregator.cj, "status", lambda: _status(False))
    monkeypatch.setattr(opportunity_aggregator.impact, "status", lambda: _status(False))
    monkeypatch.setattr(opportunity_aggregator.youtube, "status", lambda: _status(False))

    response = find_top_opportunities(
        TopOpportunityRequest(
            keywords="voice",
            include_cj=False,
            include_impact=False,
            include_verified_catalog=True,
            include_youtube=False,
        )
    )

    assert response.opportunities
    item = response.opportunities[0]
    assert item.advertiser == "ElevenLabs"
    assert item.commission_percent == 22.0
    assert item.recurring is True
    assert item.verified_at == "2026-08-11"


def test_youtube_signal_adjusts_opportunity_score(monkeypatch) -> None:
    monkeypatch.setattr(opportunity_aggregator.cj, "status", lambda: _status(False))
    monkeypatch.setattr(opportunity_aggregator.impact, "status", lambda: _status(False))
    monkeypatch.setattr(opportunity_aggregator.youtube, "status", lambda: _status(True))
    monkeypatch.setattr(
        opportunity_aggregator.youtube,
        "research_market",
        lambda query: _youtube_signal(query.query),
    )

    response = find_top_opportunities(
        TopOpportunityRequest(
            keywords="voice",
            include_cj=False,
            include_impact=False,
            include_verified_catalog=True,
            include_youtube=True,
            youtube_probe_count=1,
        )
    )

    item = response.opportunities[0]
    assert item.market_interest_score == 90.0
    assert item.market_competition_score == 30.0
    assert item.opportunity_score > item.commercial_readiness_score


def _status(configured: bool):
    from app.connectors.base import ConnectorStatus

    return ConnectorStatus(name="test", configured=configured, note="test")


def _youtube_signal(query: str):
    from app.connectors.youtube import YouTubeMarketSignal

    return YouTubeMarketSignal(
        query=query,
        sample_size=15,
        median_views=250000,
        max_views=1200000,
        recent_videos_90d=8,
        high_view_videos=6,
        established_videos=3,
        interest_score=90.0,
        competition_score=30.0,
        evidence=["test market signal"],
    )
