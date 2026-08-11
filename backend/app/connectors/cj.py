import json
import os
from dataclasses import dataclass
from datetime import datetime
from xml.etree import ElementTree as ET

import httpx
from pydantic import BaseModel, Field

from app.connectors.base import ConnectorStatus

CJ_LINK_SEARCH_URL = "https://link-search.api.cj.com/v2/link-search"
CJ_COMMISSION_API_URL = "https://commissions.api.cj.com/query"


class CJConfigurationError(RuntimeError):
    pass


class CJAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class CJConfig:
    token: str
    website_id: str
    link_search_url: str = CJ_LINK_SEARCH_URL


@dataclass(frozen=True)
class CJCommissionConfig:
    token: str
    publisher_id: str
    commission_api_url: str = CJ_COMMISSION_API_URL


class CJLinkSearchQuery(BaseModel):
    keywords: str | None = Field(default=None, max_length=200)
    advertiser_ids: str = Field(default="joined", min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=200)
    link_type: str | None = Field(default=None, max_length=100)
    promotion_type: str | None = Field(default=None, max_length=100)
    targeted_country: str | None = Field(default=None, min_length=2, max_length=2)
    allow_deep_linking: bool | None = None
    page_number: int = Field(default=1, ge=1)
    records_per_page: int = Field(default=25, ge=1, le=100)


class CJLink(BaseModel):
    advertiser_id: str | None
    advertiser_name: str | None
    link_id: str | None
    link_name: str | None
    category: str | None
    link_type: str | None
    relationship_status: str | None
    sale_commission: str | None
    lead_commission: str | None
    click_commission: str | None
    seven_day_epc_per_100_clicks: float | None
    seven_day_epc_per_click: float | None
    three_month_epc_per_100_clicks: float | None
    three_month_epc_per_click: float | None
    click_url: str | None
    destination_url: str | None
    allow_deep_linking: bool
    targeted_countries: str | None
    promotion_type: str | None


class CJLinkSearchResponse(BaseModel):
    total_matched: int
    records_returned: int
    page_number: int
    links: list[CJLink]


class CJCommissionRecord(BaseModel):
    commission_id: str
    original_action_id: str | None
    original: bool | None
    action_status: str | None
    validation_status: str | None
    action_type: str | None
    action_tracker_id: str | None
    action_tracker_name: str | None
    advertiser_id: str | None
    advertiser_name: str | None
    publisher_id: str | None
    website_id: str | None
    website_name: str | None
    order_id: str | None
    shopper_id: str | None
    source: str | None
    posting_date: str | None
    event_date: str | None
    sale_amount_usd: float
    commission_amount_usd: float


class CJCommissionResponse(BaseModel):
    count: int
    payload_complete: bool
    max_commission_id: str | None
    records: list[CJCommissionRecord]


def status() -> ConnectorStatus:
    configured = bool(os.getenv("CJ_API_TOKEN") and os.getenv("CJ_WEBSITE_ID"))
    return ConnectorStatus(
        name="cj",
        configured=configured,
        note=(
            "Live CJ Link Search is ready. Set CJ_API_TOKEN and CJ_WEBSITE_ID."
            if not configured
            else "Live CJ Link Search is configured."
        ),
    )


def commission_status() -> ConnectorStatus:
    configured = bool(os.getenv("CJ_API_TOKEN") and os.getenv("CJ_PUBLISHER_ID"))
    return ConnectorStatus(
        name="cj_commissions",
        configured=configured,
        note=(
            "CJ commission sync is ready. Set CJ_API_TOKEN and CJ_PUBLISHER_ID."
            if not configured
            else "CJ commission sync is configured."
        ),
    )


def config_from_env() -> CJConfig:
    token = os.getenv("CJ_API_TOKEN", "").strip()
    website_id = os.getenv("CJ_WEBSITE_ID", "").strip()
    if not token or not website_id:
        raise CJConfigurationError(
            "CJ connector is not configured. Set CJ_API_TOKEN and CJ_WEBSITE_ID on the backend."
        )
    return CJConfig(
        token=token,
        website_id=website_id,
        link_search_url=os.getenv("CJ_LINK_SEARCH_URL", CJ_LINK_SEARCH_URL).strip(),
    )


def commission_config_from_env() -> CJCommissionConfig:
    token = os.getenv("CJ_API_TOKEN", "").strip()
    publisher_id = os.getenv("CJ_PUBLISHER_ID", "").strip()
    if not token or not publisher_id:
        raise CJConfigurationError(
            "CJ commission sync is not configured. Set CJ_API_TOKEN and CJ_PUBLISHER_ID."
        )
    return CJCommissionConfig(
        token=token,
        publisher_id=publisher_id,
        commission_api_url=os.getenv(
            "CJ_COMMISSION_API_URL",
            CJ_COMMISSION_API_URL,
        ).strip(),
    )


def search_links(
    query: CJLinkSearchQuery,
    *,
    config: CJConfig | None = None,
    client: httpx.Client | None = None,
) -> CJLinkSearchResponse:
    resolved_config = config or config_from_env()
    params = _build_params(query, resolved_config.website_id)
    headers = {"Authorization": f"Bearer {resolved_config.token}"}

    owns_client = client is None
    http_client = client or httpx.Client(timeout=20.0)
    try:
        try:
            response = http_client.get(
                resolved_config.link_search_url,
                params=params,
                headers=headers,
            )
        except httpx.RequestError as exc:
            raise CJAPIError("Could not reach the CJ Link Search API.") from exc
    finally:
        if owns_client:
            http_client.close()

    _raise_for_status(response, "CJ Link Search")
    return parse_link_search_xml(response.text)


def list_commissions(
    since_posting_date: datetime,
    before_posting_date: datetime,
    *,
    since_commission_id: str | None = None,
    config: CJCommissionConfig | None = None,
    client: httpx.Client | None = None,
) -> CJCommissionResponse:
    resolved = config or commission_config_from_env()
    query = _commission_query(
        resolved.publisher_id,
        since_posting_date.isoformat(),
        before_posting_date.isoformat(),
        since_commission_id,
    )
    headers = {
        "Authorization": f"Bearer {resolved.token}",
        "Content-Type": "application/json",
    }
    owns_client = client is None
    http_client = client or httpx.Client(timeout=30.0)
    try:
        try:
            response = http_client.post(
                resolved.commission_api_url,
                json={"query": query},
                headers=headers,
            )
        except httpx.RequestError as exc:
            raise CJAPIError("Could not reach the CJ Commission Detail API.") from exc
    finally:
        if owns_client:
            http_client.close()

    _raise_for_status(response, "CJ Commission Detail")
    try:
        payload = response.json()
    except ValueError as exc:
        raise CJAPIError("CJ Commission Detail returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise CJAPIError("CJ Commission Detail returned an unexpected response shape.")
    if payload.get("errors"):
        raise CJAPIError("CJ Commission Detail returned a GraphQL error.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise CJAPIError("CJ Commission Detail response did not contain data.")
    commissions = data.get("publisherCommissions")
    if not isinstance(commissions, dict):
        raise CJAPIError("CJ Commission Detail response did not contain publisherCommissions.")

    raw_records = commissions.get("records")
    records = []
    if isinstance(raw_records, list):
        records = [
            _parse_commission_record(item)
            for item in raw_records
            if isinstance(item, dict)
        ]
    return CJCommissionResponse(
        count=_optional_int(commissions.get("count")) or len(records),
        payload_complete=_bool_value(commissions.get("payloadComplete")),
        max_commission_id=_string(commissions.get("maxCommissionId")),
        records=records,
    )


def parse_link_search_xml(payload: str) -> CJLinkSearchResponse:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise CJAPIError("CJ returned invalid XML.") from exc

    links_node = _first_descendant(root, "links")
    if links_node is None:
        raise CJAPIError("CJ response did not contain a links collection.")

    links: list[CJLink] = []
    for candidate in _direct_children(links_node, "link"):
        node = candidate
        if _text(node, "advertiser-id") is None:
            nested = _first_direct_child(node, "link")
            if nested is not None and _text(nested, "advertiser-id") is not None:
                node = nested

        seven_day_epc = _parse_number(_text(node, "seven-day-epc"))
        three_month_epc = _parse_number(_text(node, "three-month-epc"))
        links.append(
            CJLink(
                advertiser_id=_clean(_text(node, "advertiser-id")),
                advertiser_name=_clean(_text(node, "advertiser-name")),
                link_id=_clean(_text(node, "link-id")),
                link_name=_clean(_text(node, "link-name")),
                category=_clean(_text(node, "category")),
                link_type=_clean(_text(node, "link-type")),
                relationship_status=_clean(_text(node, "relationship-status")),
                sale_commission=_clean(_text(node, "sale-commission")),
                lead_commission=_clean(_text(node, "lead-commission")),
                click_commission=_clean(_text(node, "click-commission")),
                seven_day_epc_per_100_clicks=seven_day_epc,
                seven_day_epc_per_click=_per_click(seven_day_epc),
                three_month_epc_per_100_clicks=three_month_epc,
                three_month_epc_per_click=_per_click(three_month_epc),
                click_url=_clean(_text_any(node, "clickUrl", "click-url")),
                destination_url=_clean(_text(node, "destination")),
                allow_deep_linking=_parse_bool(_text(node, "allow-deep-linking")),
                targeted_countries=_clean(_text(node, "targeted-countries")),
                promotion_type=_clean(_text(node, "promotion-type")),
            )
        )

    return CJLinkSearchResponse(
        total_matched=_attribute_int(links_node, "total-matched"),
        records_returned=_attribute_int(links_node, "records-returned", fallback=len(links)),
        page_number=_attribute_int(links_node, "page-number", fallback=1),
        links=links,
    )


def _commission_query(
    publisher_id: str,
    since_posting_date: str,
    before_posting_date: str,
    since_commission_id: str | None,
) -> str:
    arguments = [
        f"forPublishers: [{json.dumps(publisher_id)}]",
        f"sincePostingDate: {json.dumps(since_posting_date)}",
        f"beforePostingDate: {json.dumps(before_posting_date)}",
    ]
    if since_commission_id:
        arguments.append(f"sinceCommissionId: {json.dumps(since_commission_id)}")
    joined = ",\n      ".join(arguments)
    return f"""
query {{
  publisherCommissions(
      {joined}
  ) {{
    count
    payloadComplete
    maxCommissionId
    records {{
      commissionId
      originalActionId
      original
      actionStatus
      validationStatus
      actionType
      actionTrackerId
      actionTrackerName
      advertiserId
      advertiserName
      publisherId
      websiteId
      websiteName
      orderId
      shopperId
      source
      postingDate
      eventDate
      saleAmountUsd
      pubCommissionAmountUsd
    }}
  }}
}}
""".strip()


def _parse_commission_record(item: dict[str, object]) -> CJCommissionRecord:
    commission_id = _string(item.get("commissionId"))
    if not commission_id:
        raise CJAPIError("CJ commission record did not include commissionId.")
    return CJCommissionRecord(
        commission_id=commission_id,
        original_action_id=_string(item.get("originalActionId")),
        original=_optional_bool(item.get("original")),
        action_status=_string(item.get("actionStatus")),
        validation_status=_string(item.get("validationStatus")),
        action_type=_string(item.get("actionType")),
        action_tracker_id=_string(item.get("actionTrackerId")),
        action_tracker_name=_string(item.get("actionTrackerName")),
        advertiser_id=_string(item.get("advertiserId")),
        advertiser_name=_string(item.get("advertiserName")),
        publisher_id=_string(item.get("publisherId")),
        website_id=_string(item.get("websiteId")),
        website_name=_string(item.get("websiteName")),
        order_id=_string(item.get("orderId")),
        shopper_id=_string(item.get("shopperId")),
        source=_string(item.get("source")),
        posting_date=_string(item.get("postingDate")),
        event_date=_string(item.get("eventDate")),
        sale_amount_usd=_float_value(item.get("saleAmountUsd")),
        commission_amount_usd=_float_value(item.get("pubCommissionAmountUsd")),
    )


def _raise_for_status(response: httpx.Response, label: str) -> None:
    if response.status_code in {401, 403}:
        raise CJAPIError(f"{label} rejected the credentials or API access is unavailable.")
    if response.status_code == 429:
        raise CJAPIError(f"{label} rate limit reached. Wait before trying again.")
    if response.status_code >= 400:
        raise CJAPIError(f"{label} returned HTTP {response.status_code}.")


def _build_params(query: CJLinkSearchQuery, website_id: str) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "website-id": website_id,
        "advertiser-ids": query.advertiser_ids,
        "page-number": query.page_number,
        "records-per-page": query.records_per_page,
    }
    optional = {
        "keywords": query.keywords,
        "category": query.category,
        "link-type": query.link_type,
        "promotion-type": query.promotion_type,
        "targeted-country": query.targeted_country.upper() if query.targeted_country else None,
        "allow-deep-linking": (
            str(query.allow_deep_linking).lower()
            if query.allow_deep_linking is not None
            else None
        ),
    }
    params.update({key: value for key, value in optional.items() if value is not None})
    return params


def _tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _direct_children(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(node) if _tag_name(child.tag) == name]


def _first_direct_child(node: ET.Element, name: str) -> ET.Element | None:
    return next(iter(_direct_children(node, name)), None)


def _first_descendant(node: ET.Element, name: str) -> ET.Element | None:
    for child in node.iter():
        if _tag_name(child.tag) == name:
            return child
    return None


def _text(node: ET.Element, name: str) -> str | None:
    child = _first_direct_child(node, name)
    return child.text.strip() if child is not None and child.text else None


def _text_any(node: ET.Element, *names: str) -> str | None:
    for name in names:
        value = _text(node, name)
        if value is not None:
            return value
    return None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return None if stripped.lower() in {"", "n/a", "null", "none"} else stripped


def _parse_number(value: str | None) -> float | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    normalized = cleaned.replace("$", "").replace(",", "")
    try:
        return float(normalized)
    except ValueError:
        return None


def _per_click(epc_per_100_clicks: float | None) -> float | None:
    return round(epc_per_100_clicks / 100, 6) if epc_per_100_clicks is not None else None


def _parse_bool(value: str | None) -> bool:
    return bool(value and value.strip().lower() in {"true", "yes", "1"})


def _attribute_int(node: ET.Element, name: str, fallback: int = 0) -> int:
    try:
        return int(node.attrib.get(name, fallback))
    except (TypeError, ValueError):
        return fallback


def _string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_value(value: object) -> float:
    if value is None or str(value).strip() == "":
        return 0.0
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return 0.0


def _optional_int(value: object) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        return None


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _optional_bool(value: object) -> bool | None:
    if value is None or str(value).strip() == "":
        return None
    return _bool_value(value)
