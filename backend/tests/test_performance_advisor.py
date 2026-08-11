from fastapi.testclient import TestClient

from app.main import app
from app.services import campaign_workspace as workspace
from app.services import performance_advisor as advisor


def _campaign(name: str, *, status: str = "active") -> workspace.CampaignDetail:
    return workspace.create_campaign(
        workspace.CampaignCreate(
            name=name,
            product_name=name,
            affiliate_url="https://merchant.example/track",
            status=status,
            source="test",
        )
    )


def _clicks(campaign: workspace.CampaignDetail, count: int) -> None:
    for _ in range(count):
        workspace.record_click(campaign.campaign.slug, user_agent="Mozilla/5.0")


def _conversion(
    campaign: workspace.CampaignDetail,
    amount: float,
    *,
    currency: str = "USD",
    external_id: str,
) -> None:
    workspace.add_conversion(
        campaign.campaign.id,
        workspace.ConversionCreate(
            commission_amount=amount,
            currency=currency,
            status="approved",
            network="test",
            external_id=external_id,
        ),
    )


def test_advisor_detects_relative_winner_and_zero_conversion_loser(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))
    winner = _campaign("Winner")
    weaker = _campaign("Weaker")
    loser = _campaign("Loser")

    _clicks(winner, 50)
    _conversion(winner, 50, external_id="w-1")
    _conversion(winner, 50, external_id="w-2")

    _clicks(weaker, 50)
    _conversion(weaker, 10, external_id="m-1")
    _conversion(weaker, 10, external_id="m-2")

    _clicks(loser, 80)

    result = advisor.analyze_portfolio(
        advisor.AdvisorSettings(min_sample_clicks=50, stop_clicks=80)
    )
    by_name = {item.campaign_name: item for item in result.recommendations}

    assert by_name["Winner"].classification == "winner"
    assert by_name["Winner"].recommended_action == "scale"
    assert by_name["Loser"].classification == "loser"
    assert by_name["Loser"].recommended_action == "pause_or_rework"
    assert result.summary.winners == 1
    assert result.summary.losers == 1
    assert result.summary.leaders_by_currency[0].campaign_name == "Winner"


def test_advisor_keeps_currency_comparisons_separate(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))
    euro = _campaign("Euro")
    dollar = _campaign("Dollar")
    _clicks(euro, 50)
    _clicks(dollar, 50)
    _conversion(euro, 25, currency="EUR", external_id="eur-1")
    _conversion(euro, 25, currency="EUR", external_id="eur-2")
    _conversion(dollar, 100, currency="USD", external_id="usd-1")
    _conversion(dollar, 100, currency="USD", external_id="usd-2")

    result = advisor.analyze_portfolio(
        advisor.AdvisorSettings(min_sample_clicks=50, stop_clicks=100)
    )

    assert {leader.currency for leader in result.summary.leaders_by_currency} == {"EUR", "USD"}
    assert all(item.classification != "winner" for item in result.recommendations)


def test_performance_endpoint_returns_recommendations(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))
    campaign = _campaign("API Campaign")
    _clicks(campaign, 10)

    response = TestClient(app).get(
        "/api/v1/performance/recommendations?min_sample_clicks=20&stop_clicks=40"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_campaigns"] == 1
    assert payload["recommendations"][0]["classification"] == "insufficient_data"
