import httpx
import pytest

from app.connectors.impact import (
    ImpactAPIError,
    ImpactConfig,
    list_ads,
    list_programs,
)

PROGRAMS_JSON = {
    "@page": "1",
    "@pagesize": "2",
    "@total": "2",
    "Campaigns": [
        {
            "AdvertiserId": "123",
            "AdvertiserName": "Acme AI",
            "AdvertiserUrl": "https://acme.example",
            "CampaignId": "1000",
            "CampaignName": "Acme AI Partner Program",
            "CampaignUrl": "https://acme.example/affiliate",
            "CampaignDescription": "AI software for small businesses",
            "ContractStatus": "Active",
            "TrackingLink": "https://acme.sjv.io/c/1/2/1000",
            "AllowsDeeplinking": "true",
            "ShippingRegions": ["US", "UK"],
            "DeeplinkDomains": {"DeeplinkDomain": ["acme.example"]},
        }
    ],
}

ADS_JSON = {
    "@page": "1",
    "@pagesize": "1",
    "@total": "1",
    "Ads": [
        {
            "Id": "77",
            "Name": "Acme text link",
            "CampaignId": "1000",
            "CampaignName": "Acme AI Partner Program",
            "Type": "TEXT_LINK",
            "TrackingLink": "https://acme.sjv.io/c/1/77/1000",
            "LandingPageUrl": "https://acme.example/ai",
            "AdvertiserId": "123",
            "AdvertiserName": "Acme AI",
        }
    ],
}


def test_list_programs_uses_basic_auth_and_parses_programs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/Mediapartners/IR123/Campaigns"
        assert request.url.params["Page"] == "1"
        assert request.url.params["PageSize"] == "50"
        assert request.headers["Authorization"].startswith("Basic ")
        return httpx.Response(200, json=PROGRAMS_JSON)

    config = ImpactConfig(
        account_sid="IR123",
        auth_token="secret",
        api_base_url="https://api.impact.test",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = list_programs(page=1, page_size=50, config=config, client=client)

    assert result.total == 2
    assert len(result.programs) == 1
    program = result.programs[0]
    assert program.advertiser_name == "Acme AI"
    assert program.contract_status == "Active"
    assert program.allows_deeplinking is True
    assert program.deeplink_domains == ["acme.example"]


def test_list_ads_filters_campaign_and_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["CampaignId"] == "1000"
        assert request.url.params["Type"] == "TEXT_LINK"
        return httpx.Response(200, json=ADS_JSON)

    config = ImpactConfig(
        account_sid="IR123",
        auth_token="secret",
        api_base_url="https://api.impact.test",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = list_ads(
            campaign_id="1000",
            ad_type="text_link",
            config=config,
            client=client,
        )

    assert result.ads[0].tracking_link == "https://acme.sjv.io/c/1/77/1000"


def test_impact_auth_failure_is_safe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, request=request)

    config = ImpactConfig(
        account_sid="IR123",
        auth_token="do-not-leak",
        api_base_url="https://api.impact.test",
    )
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ImpactAPIError, match="rejected the credentials"),
    ):
        list_programs(config=config, client=client)
