import os
from dataclasses import dataclass
from xml.etree import ElementTree as ET

import httpx
from pydantic import BaseModel, Field

from app.connectors.base import ConnectorStatus

CJ_LINK_SEARCH_URL = "https://link-search.api.cj.com/v2/link-search"


class CJConfigurationError(RuntimeError):
    pass


class CJAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class CJConfig:
    token: str
    website_id: str
    link_search_url: str = CJ_LINK_SEARCH_URL


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

    if response.status_code in {401, 403}:
        raise CJAPIError("CJ rejected the credentials or this publisher does not have API access.")
    if response.status_code == 429:
        raise CJAPIError("CJ rate limit reached. Wait before searching again.")
    if response.status_code >= 400:
        raise CJAPIError(f"CJ Link Search returned HTTP {response.status_code}.")

    return parse_link_search_xml(response.text)


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
