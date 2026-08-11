import os
from dataclasses import dataclass
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

from app.connectors.base import ConnectorStatus

IMPACT_API_BASE_URL = "https://api.impact.com"
IMPACT_API_VERSION = "15"


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
    contract_uri: str | None
    public_terms_uri: str | None
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


class ImpactPayoutTerm(BaseModel):
    tracker_name: str | None
    tracker_type: str | None
    payout_percentage: float | None
    payout_amount: float | None
    payout_currency: str | None
    referral_period: int | None
    referral_period_unit: str | None
    payout_amount_lower_limit: float | None
    payout_amount_upper_limit: float | None
    payout_percentage_lower_limit: float | None
    payout_percentage_upper_limit: float | None


class ImpactPublicTerms(BaseModel):
    id: str | None
    name: str | None
    campaign_id: str | None
    campaign_name: str | None
    payout_terms: list[ImpactPayoutTerm] = Field(default_factory=list)
    pdf_uri: str | None
    uri: str | None


class ImpactAction(BaseModel):
    id: str
    campaign_id: str | None
    campaign_name: str | None
    action_tracker_id: str | None
    action_tracker_name: str | None
    state: str | None
    payout: float
    amount: float
    currency: str
    event_date: str | None
    creation_date: str | None
    locking_date: str | None
    cleared_date: str | None
    oid: str | None
    sub_id1: str | None
    sub_id2: str | None
    sub_id3: str | None
    shared_id: str | None
    ad_id: str | None
    referring_domain: str | None


class ImpactActionListResponse(BaseModel):
    page: int
    page_size: int
    total: int | None
    num_pages: int | None
    actions: list[ImpactAction]


class ImpactTrackingLink(BaseModel):
    tracking_url: str


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
    payload = _request_json(
        "GET",
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
    payload = _request_json(
        "GET",
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


def get_public_terms(
    campaign_id: str,
    *,
    config: ImpactConfig | None = None,
    client: httpx.Client | None = None,
) -> ImpactPublicTerms:
    resolved = config or config_from_env()
    payload = _request_json(
        "GET",
        (
            f"{resolved.api_base_url}/Mediapartners/{resolved.account_sid}"
            f"/Campaigns/{campaign_id}/PublicTerms"
        ),
        params={},
        config=resolved,
        client=client,
    )
    return _parse_public_terms(payload)


def list_actions(
    start_date: datetime,
    end_date: datetime,
    *,
    page: int = 1,
    config: ImpactConfig | None = None,
    client: httpx.Client | None = None,
) -> ImpactActionListResponse:
    resolved = config or config_from_env()
    payload = _request_json(
        "GET",
        f"{resolved.api_base_url}/Mediapartners/{resolved.account_sid}/Actions",
        params={
            "StartDate": start_date.isoformat(),
            "EndDate": end_date.isoformat(),
            "Page": page,
        },
        config=resolved,
        client=client,
    )
    records = _as_list_with_keys(payload.get("Actions"), ("Action", "Actions"))
    actions = [_parse_action(item) for item in records if isinstance(item, dict)]
    return ImpactActionListResponse(
        page=_int_meta(payload, "@page", page),
        page_size=_int_meta(payload, "@pagesize", len(actions)),
        total=_optional_int(payload.get("@total")),
        num_pages=_optional_int(payload.get("@numpages")),
        actions=actions,
    )


def create_tracking_link(
    program_id: str,
    *,
    sub_id1: str,
    deep_link: str | None = None,
    media_property_id: str | None = None,
    config: ImpactConfig | None = None,
    client: httpx.Client | None = None,
) -> ImpactTrackingLink:
    resolved = config or config_from_env()
    params: dict[str, str] = {"subId1": sub_id1}
    if deep_link:
        params["DeepLink"] = deep_link
    if media_property_id:
        params["MediaPartnerPropertyId"] = media_property_id
    payload = _request_json(
        "POST",
        (
            f"{resolved.api_base_url}/Mediapartners/{resolved.account_sid}"
            f"/Programs/{program_id}/TrackingLinks"
        ),
        params=params,
        config=resolved,
        client=client,
    )
    tracking_url = _string(payload.get("TrackingURL"))
    if not tracking_url:
        raise ImpactAPIError("Impact tracking-link response did not include TrackingURL.")
    return ImpactTrackingLink(tracking_url=tracking_url)


def _request_json(
    method: str,
    url: str,
    *,
    params: dict[str, str | int],
    config: ImpactConfig,
    client: httpx.Client | None,
) -> dict[str, object]:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=30.0)
    try:
        try:
            response = http_client.request(
                method,
                url,
                params=params,
                auth=httpx.BasicAuth(config.account_sid, config.auth_token),
                headers={"Accept": "application/json", "IR-Version": IMPACT_API_VERSION},
            )
        except httpx.RequestError as exc:
            raise ImpactAPIError("Could not reach the Impact Partner API.") from exc
    finally:
        if owns_client:
            http_client.close()

    if response.status_code in {401, 403}:
        raise ImpactAPIError("Impact rejected the credentials or API access is unavailable.")
    if response.status_code == 404:
        raise ImpactAPIError("Impact resource was not found or is not available to this account.")
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
        contract_uri=_string(item.get("ContractUri")),
        public_terms_uri=_string(item.get("PublicTermsUri")),
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


def _parse_public_terms(item: dict[str, object]) -> ImpactPublicTerms:
    payout_terms_raw = _as_list_with_keys(
        item.get("PayoutTermsList"),
        ("PayoutTerm", "PayoutTerms"),
    )
    return ImpactPublicTerms(
        id=_string(item.get("Id")),
        name=_string(item.get("Name")),
        campaign_id=_string(item.get("CampaignId")),
        campaign_name=_string(item.get("CampaignName")),
        payout_terms=[
            _parse_payout_term(term) for term in payout_terms_raw if isinstance(term, dict)
        ],
        pdf_uri=_string(item.get("PdfUri")),
        uri=_string(item.get("Uri")),
    )


def _parse_payout_term(item: dict[str, object]) -> ImpactPayoutTerm:
    return ImpactPayoutTerm(
        tracker_name=_string(item.get("TrackerName")),
        tracker_type=_string(item.get("TrackerType")),
        payout_percentage=_optional_float(item.get("PayoutPercentage")),
        payout_amount=_optional_float(item.get("PayoutAmount")),
        payout_currency=_string(item.get("PayoutCurrency")),
        referral_period=_optional_int(item.get("ReferralPeriod")),
        referral_period_unit=_string(item.get("ReferralPeriodUnit")),
        payout_amount_lower_limit=_optional_float(item.get("PayoutAmountLowerLimit")),
        payout_amount_upper_limit=_optional_float(item.get("PayoutAmountUpperLimit")),
        payout_percentage_lower_limit=_optional_float(item.get("PayoutPercentageLowerLimit")),
        payout_percentage_upper_limit=_optional_float(item.get("PayoutPercentageUpperLimit")),
    )


def _parse_action(item: dict[str, object]) -> ImpactAction:
    action_id = _string(item.get("Id"))
    if not action_id:
        raise ImpactAPIError("Impact action did not include Id.")
    return ImpactAction(
        id=action_id,
        campaign_id=_string(item.get("CampaignId")),
        campaign_name=_string(item.get("CampaignName")),
        action_tracker_id=_string(item.get("ActionTrackerId")),
        action_tracker_name=_string(item.get("ActionTrackerName")),
        state=_string(item.get("State")),
        payout=_float_value(item.get("Payout")),
        amount=_float_value(item.get("Amount")),
        currency=(_string(item.get("Currency")) or "USD").upper(),
        event_date=_string(item.get("EventDate")),
        creation_date=_string(item.get("CreationDate")),
        locking_date=_string(item.get("LockingDate")),
        cleared_date=_string(item.get("ClearedDate")),
        oid=_string(item.get("Oid")),
        sub_id1=_string(item.get("SubId1")),
        sub_id2=_string(item.get("SubId2")),
        sub_id3=_string(item.get("SubId3")),
        shared_id=_string(item.get("SharedId")),
        ad_id=_string(item.get("AdId")),
        referring_domain=_string(item.get("ReferringDomain")),
    )


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("Campaign", "Ad", "Action"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
            if isinstance(nested, dict):
                return [nested]
    return []


def _as_list_with_keys(value: object, keys: tuple[str, ...]) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in keys:
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
            if isinstance(nested, dict):
                return [nested]
        if any(key in value for key in ("TrackerName", "TrackerType", "Id", "State")):
            return [value]
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
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        return None


def _optional_float(value: object) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _float_value(value: object) -> float:
    return _optional_float(value) or 0.0


def _int_meta(payload: dict[str, object], key: str, fallback: int) -> int:
    value = _optional_int(payload.get(key))
    return fallback if value is None else value
