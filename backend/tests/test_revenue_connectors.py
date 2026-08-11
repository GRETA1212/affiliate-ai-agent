from datetime import UTC, datetime

import httpx
import pytest

from app.connectors.cj import (
    CJCommissionConfig,
    CJConfigurationError,
    commission_config_from_env,
    list_commissions,
)
from app.connectors.impact import ImpactConfig, create_tracking_link, list_actions


def test_cj_commission_api_parses_publisher_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret-token"
        body = request.content.decode()
        assert "publisherCommissions" in body
        assert "forPublishers" in body
        assert "999" in body
        return httpx.Response(
            200,
            json={
                "data": {
                    "publisherCommissions": {
                        "count": 2,
                        "payloadComplete": True,
                        "maxCommissionId": "456",
                        "records": [
                            {
                                "commissionId": "455",
                                "originalActionId": "action-1",
                                "original": True,
                                "actionStatus": "closed",
                                "validationStatus": "approved",
                                "actionType": "sale",
                                "advertiserId": "55",
                                "advertiserName": "Example AI",
                                "orderId": "order-1",
                                "shopperId": "campaign-slug",
                                "postingDate": "2026-08-11T12:00:00Z",
                                "eventDate": "2026-08-11T11:00:00Z",
                                "saleAmountUsd": 100,
                                "pubCommissionAmountUsd": 20,
                            },
                            {
                                "commissionId": "456",
                                "originalActionId": "action-1",
                                "original": False,
                                "actionStatus": "closed",
                                "validationStatus": "approved",
                                "actionType": "sale",
                                "advertiserId": "55",
                                "advertiserName": "Example AI",
                                "orderId": "order-1",
                                "postingDate": "2026-08-11T12:05:00Z",
                                "eventDate": "2026-08-11T11:00:00Z",
                                "saleAmountUsd": -100,
                                "pubCommissionAmountUsd": -20,
                            },
                        ],
                    }
                }
            },
        )

    config = CJCommissionConfig(
        token="secret-token",
        publisher_id="999",
        commission_api_url="https://commissions.example/query",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = list_commissions(
            datetime(2026, 8, 10, tzinfo=UTC),
            datetime(2026, 8, 11, tzinfo=UTC),
            config=config,
            client=client,
        )

    assert result.count == 2
    assert result.payload_complete is True
    assert result.max_commission_id == "456"
    assert result.records[0].shopper_id == "campaign-slug"
    assert result.records[1].commission_amount_usd == -20


def test_missing_cj_commission_configuration_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CJ_API_TOKEN", raising=False)
    monkeypatch.delenv("CJ_PUBLISHER_ID", raising=False)

    with pytest.raises(CJConfigurationError, match="CJ commission sync is not configured"):
        commission_config_from_env()


def test_impact_actions_parse_state_payout_and_subid() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/Mediapartners/IR123/Actions"
        assert "StartDate" in request.url.params
        assert "EndDate" in request.url.params
        return httpx.Response(
            200,
            json={
                "@page": "1",
                "@pagesize": "20000",
                "@total": "1",
                "@numpages": "1",
                "Actions": [
                    {
                        "Id": "1000.1",
                        "CampaignId": "1000",
                        "CampaignName": "Acme AI",
                        "ActionTrackerId": "2240",
                        "ActionTrackerName": "Sale",
                        "State": "APPROVED",
                        "Payout": "12.50",
                        "Amount": "50.00",
                        "Currency": "USD",
                        "EventDate": "2026-08-11T10:00:00Z",
                        "CreationDate": "2026-08-11T10:01:00Z",
                        "Oid": "order-1",
                        "SubId1": "campaign-slug",
                    }
                ],
            },
        )

    config = ImpactConfig(
        account_sid="IR123",
        auth_token="secret",
        api_base_url="https://api.impact.test",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = list_actions(
            datetime(2026, 8, 10, tzinfo=UTC),
            datetime(2026, 8, 11, tzinfo=UTC),
            config=config,
            client=client,
        )

    action = result.actions[0]
    assert action.state == "APPROVED"
    assert action.payout == 12.5
    assert action.sub_id1 == "campaign-slug"
    assert result.num_pages == 1


def test_impact_create_tracking_link_sends_subid() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/Mediapartners/IR123/Programs/1000/TrackingLinks"
        assert request.url.params["subId1"] == "campaign-slug"
        return httpx.Response(
            200,
            json={"TrackingURL": "https://acme.sjv.io/c/1/2/1000?subId1=campaign-slug"},
        )

    config = ImpactConfig(
        account_sid="IR123",
        auth_token="secret",
        api_base_url="https://api.impact.test",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = create_tracking_link(
            "1000",
            sub_id1="campaign-slug",
            config=config,
            client=client,
        )

    assert result.tracking_url.startswith("https://acme.sjv.io/")
