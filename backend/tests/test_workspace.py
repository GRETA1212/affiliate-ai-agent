import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import campaign_workspace as workspace


def _active_campaign(name: str = "AI Voice Test") -> workspace.CampaignCreate:
    return workspace.CampaignCreate(
        name=name,
        product_name="Example AI",
        audience="Creators",
        problem="Need better audio",
        affiliate_url="https://merchant.example/track?id=abc",
        status="active",
        source="test",
        opportunity_score=88,
    )


def test_workspace_persists_campaign_click_and_revenue(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))
    created = workspace.create_campaign(_active_campaign())

    target = workspace.record_click(
        created.campaign.slug,
        source="youtube",
        medium="video",
        user_agent="Mozilla/5.0",
    )
    workspace.record_click(created.campaign.slug, user_agent="ExampleBot crawler")
    conversion = workspace.add_conversion(
        created.campaign.id,
        workspace.ConversionCreate(
            commission_amount=25,
            sale_amount=100,
            currency="EUR",
            status="approved",
            network="impact",
            external_id="sale-001",
        ),
    )

    reloaded = workspace.list_campaigns()
    metrics = workspace.campaign_metrics(created.campaign.id)
    summary = workspace.workspace_summary()

    assert target == "https://merchant.example/track?id=abc"
    assert conversion.commission_amount == 25
    assert len(reloaded) == 1
    assert metrics.total_clicks == 2
    assert metrics.human_clicks == 1
    assert metrics.bot_clicks == 1
    assert metrics.approved_conversions == 1
    assert metrics.approved_revenue_by_currency == {"EUR": 25.0}
    assert metrics.epc_by_currency == {"EUR": 25.0}
    assert metrics.conversion_rate == 1.0
    assert summary.approved_revenue_by_currency == {"EUR": 25.0}


def test_duplicate_network_conversion_is_rejected(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))
    campaign = workspace.create_campaign(_active_campaign())
    conversion = workspace.ConversionCreate(
        commission_amount=10,
        currency="USD",
        network="cj",
        external_id="order-77",
    )
    workspace.add_conversion(campaign.campaign.id, conversion)

    with pytest.raises(workspace.WorkspaceConflict, match="already exists"):
        workspace.add_conversion(campaign.campaign.id, conversion)


def test_tracked_redirect_records_human_click(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/workspace/campaigns",
        json={
            "name": "Tracked Campaign",
            "product_name": "Example AI",
            "affiliate_url": "https://merchant.example/offer",
            "status": "active",
        },
    )
    assert create_response.status_code == 201
    campaign = create_response.json()["campaign"]

    response = client.get(
        f"/go/{campaign['slug']}?source=youtube&medium=short",
        headers={"user-agent": "Mozilla/5.0"},
        follow_redirects=False,
    )
    metrics = client.get(f"/api/v1/workspace/campaigns/{campaign['id']}/metrics")

    assert response.status_code == 302
    assert response.headers["location"] == "https://merchant.example/offer"
    assert metrics.status_code == 200
    assert metrics.json()["human_clicks"] == 1


def test_paused_campaign_does_not_redirect(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))
    campaign = workspace.create_campaign(
        workspace.CampaignCreate(
            name="Paused Campaign",
            product_name="Example AI",
            affiliate_url="https://merchant.example/offer",
            status="paused",
        )
    )

    with pytest.raises(workspace.WorkspaceInactive):
        workspace.record_click(campaign.campaign.slug)
