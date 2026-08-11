from app.connectors.direct_program import DirectProgramScan
from app.services import opportunity_aggregator
from app.services.opportunity_aggregator import TopOpportunityRequest, find_top_opportunities


def test_top_opportunities_rank_direct_program(monkeypatch) -> None:
    monkeypatch.setattr(opportunity_aggregator.cj, "status", lambda: _status(False))
    monkeypatch.setattr(opportunity_aggregator.impact, "status", lambda: _status(False))
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
        )
    )

    assert len(response.opportunities) == 1
    item = response.opportunities[0]
    assert item.source == "direct"
    assert item.commercial_readiness_score > 70
    assert item.recurring is True
    assert len(response.warnings) == 2


def _status(configured: bool):
    from app.connectors.base import ConnectorStatus

    return ConnectorStatus(name="test", configured=configured, note="test")
