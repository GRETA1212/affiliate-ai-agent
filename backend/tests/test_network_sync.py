from datetime import UTC, datetime

from app.connectors import cj, impact
from app.services import campaign_workspace as workspace
from app.services import network_sync


def _campaign(name: str) -> workspace.CampaignDetail:
    return workspace.create_campaign(
        workspace.CampaignCreate(
            name=name,
            product_name="Example AI",
            affiliate_url="https://merchant.example/track",
            status="active",
        )
    )


def test_impact_sync_matches_subid_and_updates_reversal(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))
    campaign = _campaign("Impact Sync")
    network_sync.bind_campaign(
        campaign.campaign.id,
        network_sync.CampaignBindingRequest(
            network="impact",
            program_id="1000",
        ),
    )

    state = {"value": "APPROVED"}

    def fake_actions(
        start_date: datetime,
        end_date: datetime,
        *,
        page: int = 1,
    ) -> impact.ImpactActionListResponse:
        assert start_date.tzinfo is not None
        assert end_date.tzinfo is not None
        return impact.ImpactActionListResponse(
            page=page,
            page_size=1,
            total=1,
            num_pages=1,
            actions=[
                impact.ImpactAction(
                    id="impact-action-1",
                    campaign_id="1000",
                    campaign_name="Example AI",
                    action_tracker_id="sale",
                    action_tracker_name="Sale",
                    state=state["value"],
                    payout=30,
                    amount=100,
                    currency="USD",
                    event_date="2026-08-11T12:00:00+00:00",
                    creation_date="2026-08-11T12:01:00+00:00",
                    locking_date=None,
                    cleared_date=None,
                    oid="order-1",
                    sub_id1=campaign.campaign.slug,
                    sub_id2=None,
                    sub_id3=None,
                    shared_id=None,
                    ad_id=None,
                    referring_domain=None,
                )
            ],
        )

    monkeypatch.setattr(impact, "list_actions", fake_actions)

    first = network_sync.sync_networks(
        network_sync.SyncRequest(networks=["impact"], lookback_days=7)
    )
    first_metrics = workspace.campaign_metrics(campaign.campaign.id)

    assert first.results[0].matched == 1
    assert first.results[0].conversions_upserted == 1
    assert first_metrics.approved_conversions == 1
    assert first_metrics.approved_revenue_by_currency == {"USD": 30.0}

    state["value"] = "REVERSED"
    network_sync.sync_networks(
        network_sync.SyncRequest(networks=["impact"], lookback_days=7)
    )
    second_metrics = workspace.campaign_metrics(campaign.campaign.id)

    assert second_metrics.approved_conversions == 0
    assert second_metrics.reversed_conversions == 1
    assert second_metrics.approved_revenue_by_currency == {}


def test_cj_correction_deltas_reconcile_to_reversed(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))
    campaign = _campaign("CJ Sync")
    network_sync.bind_campaign(
        campaign.campaign.id,
        network_sync.CampaignBindingRequest(
            network="cj",
            program_id="55",
        ),
    )

    def fake_commissions(
        since_posting_date: datetime,
        before_posting_date: datetime,
        *,
        since_commission_id: str | None = None,
    ) -> cj.CJCommissionResponse:
        assert since_posting_date.tzinfo is not None
        assert before_posting_date.tzinfo is not None
        assert since_commission_id is None
        common = {
            "original_action_id": "action-900",
            "action_status": "closed",
            "validation_status": "approved",
            "action_type": "sale",
            "action_tracker_id": "10",
            "action_tracker_name": "Sale",
            "advertiser_id": "55",
            "advertiser_name": "Example Advertiser",
            "publisher_id": "99",
            "website_id": "11",
            "website_name": "Example Site",
            "order_id": "order-900",
            "shopper_id": None,
            "source": None,
            "posting_date": "2026-08-11T12:00:00+00:00",
            "event_date": "2026-08-11T11:00:00+00:00",
        }
        return cj.CJCommissionResponse(
            count=2,
            payload_complete=True,
            max_commission_id="2",
            records=[
                cj.CJCommissionRecord(
                    commission_id="1",
                    original=True,
                    sale_amount_usd=100,
                    commission_amount_usd=20,
                    **common,
                ),
                cj.CJCommissionRecord(
                    commission_id="2",
                    original=False,
                    sale_amount_usd=-100,
                    commission_amount_usd=-20,
                    **common,
                ),
            ],
        )

    monkeypatch.setattr(cj, "list_commissions", fake_commissions)

    result = network_sync.sync_networks(
        network_sync.SyncRequest(networks=["cj"], lookback_days=7)
    )
    metrics = workspace.campaign_metrics(campaign.campaign.id)

    assert result.results[0].fetched == 2
    assert result.results[0].matched == 2
    assert metrics.approved_conversions == 0
    assert metrics.reversed_conversions == 1
    assert metrics.approved_revenue_by_currency == {}


def test_unmatched_event_can_be_assigned_later(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))
    campaign = _campaign("Manual Reconcile")

    def fake_actions(
        start_date: datetime,
        end_date: datetime,
        *,
        page: int = 1,
    ) -> impact.ImpactActionListResponse:
        return impact.ImpactActionListResponse(
            page=page,
            page_size=1,
            total=1,
            num_pages=1,
            actions=[
                impact.ImpactAction(
                    id="unmatched-1",
                    campaign_id="other-program",
                    campaign_name="Other",
                    action_tracker_id=None,
                    action_tracker_name=None,
                    state="APPROVED",
                    payout=12,
                    amount=50,
                    currency="EUR",
                    event_date=datetime.now(UTC).isoformat(),
                    creation_date=None,
                    locking_date=None,
                    cleared_date=None,
                    oid="order-x",
                    sub_id1="unknown-token",
                    sub_id2=None,
                    sub_id3=None,
                    shared_id=None,
                    ad_id=None,
                    referring_domain=None,
                )
            ],
        )

    monkeypatch.setattr(impact, "list_actions", fake_actions)
    network_sync.sync_networks(
        network_sync.SyncRequest(networks=["impact"], lookback_days=7)
    )

    unmatched = network_sync.list_unmatched_events()
    assert len(unmatched) == 1
    network_sync.assign_event(unmatched[0].id, campaign.campaign.id)

    metrics = workspace.campaign_metrics(campaign.campaign.id)
    assert metrics.approved_conversions == 1
    assert metrics.approved_revenue_by_currency == {"EUR": 12.0}
