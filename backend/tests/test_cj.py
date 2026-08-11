import httpx
import pytest

from app.connectors.cj import (
    CJAPIError,
    CJConfig,
    CJConfigurationError,
    CJLinkSearchQuery,
    config_from_env,
    parse_link_search_xml,
    search_links,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<cj-api>
  <links total-matched="1" records-returned="1" page-number="1">
    <link>
      <advertiser-id>12345</advertiser-id>
      <advertiser-name>Example Hosting</advertiser-name>
      <category>Web Hosting</category>
      <click-commission>0.0</click-commission>
      <lead-commission>N/A</lead-commission>
      <sale-commission>10.00%</sale-commission>
      <destination>https://example.com/vps</destination>
      <link-id>98765</link-id>
      <link-name>High Performance VPS</link-name>
      <link-type>Text Link</link-type>
      <allow-deep-linking>true</allow-deep-linking>
      <promotion-type>N/A</promotion-type>
      <relationship-status>joined</relationship-status>
      <targeted-countries>DE,US</targeted-countries>
      <seven-day-epc>$17.54</seven-day-epc>
      <three-month-epc>21.06</three-month-epc>
      <clickUrl>https://tracking.example/click</clickUrl>
    </link>
  </links>
</cj-api>
"""


def test_parse_link_search_normalizes_epc_per_click() -> None:
    result = parse_link_search_xml(SAMPLE_XML)

    assert result.total_matched == 1
    assert result.records_returned == 1
    link = result.links[0]
    assert link.advertiser_name == "Example Hosting"
    assert link.sale_commission == "10.00%"
    assert link.seven_day_epc_per_100_clicks == 17.54
    assert link.seven_day_epc_per_click == 0.1754
    assert link.three_month_epc_per_100_clicks == 21.06
    assert link.three_month_epc_per_click == 0.2106
    assert link.allow_deep_linking is True


def test_search_links_sends_token_pid_and_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret-token"
        assert request.url.params["website-id"] == "24680"
        assert request.url.params["advertiser-ids"] == "joined"
        assert request.url.params["keywords"] == "vps"
        assert request.url.params["targeted-country"] == "DE"
        return httpx.Response(200, text=SAMPLE_XML)

    query = CJLinkSearchQuery(keywords="vps", targeted_country="de")
    config = CJConfig(token="secret-token", website_id="24680")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = search_links(query, config=config, client=client)

    assert result.links[0].link_name == "High Performance VPS"


def test_missing_configuration_fails_without_leaking_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CJ_API_TOKEN", raising=False)
    monkeypatch.delenv("CJ_WEBSITE_ID", raising=False)

    with pytest.raises(CJConfigurationError, match="CJ connector is not configured"):
        config_from_env()


def test_auth_failure_becomes_safe_connector_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, request=request)

    config = CJConfig(token="bad-secret", website_id="24680")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(CJAPIError, match="rejected the credentials"):
            search_links(CJLinkSearchQuery(), config=config, client=client)
