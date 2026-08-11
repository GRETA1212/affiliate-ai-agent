import os
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, Field

from app.connectors.base import ConnectorStatus

IMPACT_API_BASE_URL = "https://api.impact.com"


class ImpactConfigurationError(RuntimeError):
    pass


class ImpactAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImpactConfig:
    account_sid: str
    auth_token: str
    api_base_url: str = IMPACT_API_BASE_URL


class ImpactProgram(BaseModel):
    advertiser_id: str | None
    advertiser_name: str | None
    advertiser_url: str | None
    campaign_id: str | None
    campaign_name: str | None
    campaign_url: str | None
    campaign_description: str | None
    contract_status: str | None
    tracking_link: str | None
    allows_deeplinking: bool
    shipping_regions: list[str] = Field(default_factory=list)
    deeplink_domains: list[str] = Field(default_factory=list)


class ImpactProgramListResponse(BaseModel):
    page: int
    page_size: int
    total: int | None
    programs: list[ImpactProgram]


class ImpactAd(BaseModel):
    id: str | None
    name: str | None
    description: str | None
    campaign_id: str | None
    campaign_name: str | None
    type: str | None
    tracking_link: str | None
    landing_page_url: str | None
    advertiser_id: str | None
    advertiser_name: str | None


class ImpactAdListResponse(BaseModel):
    page: int
    page_size: int
    total: int | None
    ads: list[ImpactAd]


def status() -> ConnectorStatus:
    configured = bool(os.getenv("IMPACT_ACCOUNT_SID") and os.getenv("IMPACT_AUTH_TOKEN"))
    return ConnectorStatus(
        name="impact",
        configured=configured,
        note=(
            "Live Impact Partner API is ready. Set IMPACT_ACCOUNT_SID and IMPACT_AUTH_TOKEN."
            if not configured
            else "Live Impact Partner API is configured."
        ),
    )


def config_from_env() -> ImpactConfig:
    account_sid = os.getenv("IMPACT_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("IMPACT_AUTH_TOKEN", "").strip()
    if not account_sid or not auth_token:
        raise ImpactConfigurationError(
            "Impact connector is not configured. Set IMPACT_ACCOUNT_SID and IMPACT_AUTH_TOKEN."
        )
    return ImpactConfig(
        account_sid=account_sid,
        auth_token=auth_token,
        api_base_url=os.getenv("IMPACT_API_BASE_URL", IMPACT_API_BASE_URL).rstrip("/"),
    )


def list_programs(
    *,
    page: int = 1,
    page_size: int = 100,
    config: ImpactConfig | None = None,
    client: httpx.Client | None = None,
) -> ImpactProgramListResponse:
    resolved = config or config_from_env()
    payload = _get_json(
        f"{resolved.api_base_url}/Mediapartners/{resolved.account_sid}/Campaigns",
        params={"Page": page, "PageSize": page_size},
        config=resolved,
        client=client,
    )
    records = _as_list(payload.get("Campaigns"))
    programs = [_parse_program(item) for item in records if isinstance(item, dict)]
    return ImpactProgramListResponse(
        page=_int_meta(payload, "@page", page),
        page_size=_int_meta(payload, "@pagesize", len(programs) or page_size),
        total=_optional_int(payload.get("@total")),
        programs=programs,
    )


def list_ads(
    *,
    campaign_id: str | None = None,
    ad_type: str | None = None,
    page: int = 1,
    page_size: int = 100,
    config: ImpactConfig | None = None,
    client: httpx.Client | None = None,
) -> ImpactAdListResponse:
    resolved = config or config_from_env()
    params: dict[str, str | int] = {"Page": page, "PageSize": page_size}
    if campaign_id:
        params["CampaignId"] = campaign_id
    if ad_type:
        params["Type"] = ad_type.upper()
    payload = _get_json(
        f"{resolved.api_base_url}/Mediapartners/{resolved.account_sid}/Ads",
        params=params,
        config=resolved,
        client=client,
    )
    records = _as_list(payload.get("Ads"))
    ads = [_parse_ad(item) for item in records if isinstance(item, dict)]
    return ImpactAdListResponse(
        page=_int_meta(payload, "@page", page),
        page_size=_int_meta(payload, "@pagesize", len(ads) or page_size),
        total=_optional_int(payload.get("@total")),
        ads=ads,
    )


def _get_json(
    url: str,
    *,
    params: dict[str, str | int],
    config: ImpactConfig,
    client: httpx.Client | None,
) -> dict[str, object]:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20.0)
    try:
        try:
            response = http_client.get(
                url,
                params=params,
                auth=httpx.BasicAuth(config.account_sid, config.auth_token),
                headers={"Accept": "application/json"},
            )
        except httpx.RequestError as exc:
            raise ImpactAPIError("Could not reach the Impact Partner API.") from exc
    finally:
        if owns_client:
            http_client.close()

    if response.status_code in {401, 403}:
        raise ImpactAPIError("Impact rejected the credentials or API access is unavailable.")
    if response.status_code == 429:
        raise ImpactAPIError("Impact rate limit reached. Wait before trying again.")
    if response.status_code >= 400:
        raise ImpactAPIError(f"Impact Partner API returned HTTP {response.status_code}.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise ImpactAPIError("Impact returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise ImpactAPIError("Impact returned an unexpected response shape.")
    return payload


def _parse_program(item: dict[str, object]) -> ImpactProgram:
    return ImpactProgram(
        advertiser_id=_string(item.get("AdvertiserId")),
        advertiser_name=_string(item.get("AdvertiserName")),
        advertiser_url=_string(item.get("AdvertiserUrl")),
        campaign_id=_string(item.get("CampaignId")),
        campaign_name=_string(item.get("CampaignName")),
        campaign_url=_string(item.get("CampaignUrl")),
        campaign_description=_string(item.get("CampaignDescription")),
        contract_status=_string(item.get("ContractStatus")),
        tracking_link=_string(item.get("TrackingLink")),
        allows_deeplinking=_bool(item.get("AllowsDeeplinking")),
        shipping_regions=_string_list(item.get("ShippingRegions")),
        deeplink_domains=_nested_string_list(item.get("DeeplinkDomains"), "DeeplinkDomain"),
    )


def _parse_ad(item: dict[str, object]) -> ImpactAd:
    return ImpactAd(
        id=_string(item.get("Id")),
        name=_string(item.get("Name")),
        description=_string(item.get("Description")),
        campaign_id=_string(item.get("CampaignId")),
        campaign_name=_string(item.get("CampaignName")),
        type=_string(item.get("Type")),
        tracking_link=_string(item.get("TrackingLink")),
        landing_page_url=_string(item.get("LandingPageUrl")),
        advertiser_id=_string(item.get("AdvertiserId")),
        advertiser_name=_string(item.get("AdvertiserName")),
    )


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("Campaign", "Ad"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
            if isinstance(nested, dict):
                return [nested]
    return []


def _string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _nested_string_list(value: object, key: str) -> list[str]:
    if isinstance(value, dict):
        return _string_list(value.get(key))
    return _string_list(value)


def _optional_int(value: object) -> int | None:
    try:
        return int(str(value)) if value is not None else None
    except ValueError:
        return None


def _int_meta(payload: dict[str, object], key: str, fallback: int) -> int:
    return _optional_int(payload.get(key)) or fallback
