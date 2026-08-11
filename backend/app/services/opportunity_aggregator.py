import re

from pydantic import BaseModel, Field, HttpUrl

from app.connectors import cj, impact
from app.connectors.direct_program import DirectProgramScanError, DirectProgramScanRequest, scan_program


class TopOpportunityRequest(BaseModel):
    keywords: str | None = Field(default=None, max_length=200)
    direct_urls: list[HttpUrl] = Field(default_factory=list, max_length=10)
    include_cj: bool = True
    include_impact: bool = True
    limit: int = Field(default=10, ge=1, le=50)


class RankedAffiliateOpportunity(BaseModel):
    source: str
    name: str
    advertiser: str | None
    program_url: str | None
    tracking_url: str | None
    commission_text: str | None
    commission_percent: float | None
    epc_per_click: float | None
    cookie_days: int | None
    recurring: bool
    commercial_readiness_score: float
    confidence: float
    reasons: list[str]


class TopOpportunityResponse(BaseModel):
    keywords: str | None
    opportunities: list[RankedAffiliateOpportunity]
    warnings: list[str]
    scoring_note: str = (
        "Commercial readiness is not a profit prediction. Demand/trend data will be added by "
        "Google Ads/Trends connectors; current ranking uses monetization and tracking evidence."
    )


def find_top_opportunities(request: TopOpportunityRequest) -> TopOpportunityResponse:
    opportunities: list[RankedAffiliateOpportunity] = []
    warnings: list[str] = []

    if request.include_cj:
        if cj.status().configured:
            try:
                result = cj.search_links(
                    cj.CJLinkSearchQuery(
                        keywords=request.keywords,
                        advertiser_ids="joined",
                        records_per_page=min(100, request.limit * 3),
                    )
                )
                opportunities.extend(_from_cj(link) for link in result.links)
            except (cj.CJAPIError, cj.CJConfigurationError) as exc:
                warnings.append(f"CJ: {exc}")
        else:
            warnings.append("CJ is not configured; skipped live CJ opportunities.")

    if request.include_impact:
        if impact.status().configured:
            try:
                result = impact.list_programs(page_size=100)
                for program in result.programs:
                    if _matches_keywords(request.keywords, program):
                        opportunities.append(_from_impact(program))
            except (impact.ImpactAPIError, impact.ImpactConfigurationError) as exc:
                warnings.append(f"Impact: {exc}")
        else:
            warnings.append("Impact is not configured; skipped live Impact programs.")

    for url in request.direct_urls:
        try:
            scanned = scan_program(DirectProgramScanRequest(url=url))
            opportunities.append(_from_direct(scanned))
        except DirectProgramScanError as exc:
            warnings.append(f"Direct scan {url}: {exc}")

    opportunities.sort(
        key=lambda item: (item.commercial_readiness_score, item.confidence),
        reverse=True,
    )
    return TopOpportunityResponse(
        keywords=request.keywords,
        opportunities=opportunities[: request.limit],
        warnings=warnings,
    )


def _from_cj(link: cj.CJLink) -> RankedAffiliateOpportunity:
    commission_percent = _parse_percent(link.sale_commission)
    epc = link.three_month_epc_per_click or link.seven_day_epc_per_click
    score, reasons, confidence = _score(
        commission_percent=commission_percent,
        epc_per_click=epc,
        cookie_days=None,
        recurring=False,
        tracking_ready=bool(link.click_url),
        source_quality=0.95,
    )
    return RankedAffiliateOpportunity(
        source="cj",
        name=link.link_name or link.advertiser_name or "CJ offer",
        advertiser=link.advertiser_name,
        program_url=link.destination_url,
        tracking_url=link.click_url,
        commission_text=link.sale_commission or link.lead_commission or link.click_commission,
        commission_percent=commission_percent,
        epc_per_click=epc,
        cookie_days=None,
        recurring=False,
        commercial_readiness_score=score,
        confidence=confidence,
        reasons=reasons,
    )


def _from_impact(program: impact.ImpactProgram) -> RankedAffiliateOpportunity:
    score, reasons, confidence = _score(
        commission_percent=None,
        epc_per_click=None,
        cookie_days=None,
        recurring=False,
        tracking_ready=bool(program.tracking_link),
        source_quality=0.9,
    )
    if program.contract_status and program.contract_status.lower() == "active":
        score = min(100.0, round(score + 6.0, 2))
        reasons.append("Active Impact contract")
    return RankedAffiliateOpportunity(
        source="impact",
        name=program.campaign_name or program.advertiser_name or "Impact program",
        advertiser=program.advertiser_name,
        program_url=program.campaign_url or program.advertiser_url,
        tracking_url=program.tracking_link,
        commission_text=None,
        commission_percent=None,
        epc_per_click=None,
        cookie_days=None,
        recurring=False,
        commercial_readiness_score=score,
        confidence=confidence,
        reasons=reasons,
    )


def _from_direct(scanned: object) -> RankedAffiliateOpportunity:
    from app.connectors.direct_program import DirectProgramScan

    if not isinstance(scanned, DirectProgramScan):
        raise TypeError("Expected DirectProgramScan")
    score, reasons, confidence = _score(
        commission_percent=scanned.commission_percent,
        epc_per_click=None,
        cookie_days=scanned.cookie_days,
        recurring=scanned.recurring,
        tracking_ready=bool(scanned.application_url),
        source_quality=0.65,
    )
    reasons.extend(scanned.evidence[:3])
    return RankedAffiliateOpportunity(
        source="direct",
        name=scanned.title or _domain_name(scanned.final_url),
        advertiser=_domain_name(scanned.final_url),
        program_url=scanned.final_url,
        tracking_url=None,
        commission_text=scanned.commission_text,
        commission_percent=scanned.commission_percent,
        epc_per_click=None,
        cookie_days=scanned.cookie_days,
        recurring=scanned.recurring,
        commercial_readiness_score=score,
        confidence=min(confidence, scanned.confidence),
        reasons=_dedupe(reasons),
    )


def _score(
    *,
    commission_percent: float | None,
    epc_per_click: float | None,
    cookie_days: int | None,
    recurring: bool,
    tracking_ready: bool,
    source_quality: float,
) -> tuple[float, list[str], float]:
    reasons: list[str] = []
    monetization_values: list[float] = []
    known_fields = 0

    if commission_percent is not None:
        monetization_values.append(min(100.0, commission_percent * 2.0))
        reasons.append(f"Commission detected: {commission_percent:g}%")
        known_fields += 1
    if epc_per_click is not None:
        monetization_values.append(min(100.0, epc_per_click * 100.0))
        reasons.append(f"Historical network EPC ≈ {epc_per_click:.3f} per click")
        known_fields += 1
    monetization = max(monetization_values, default=35.0)

    cookie_score = 35.0
    if cookie_days is not None:
        cookie_score = min(100.0, cookie_days / 90.0 * 100.0)
        reasons.append(f"Cookie/attribution window: {cookie_days} days")
        known_fields += 1

    recurring_score = 100.0 if recurring else 35.0
    if recurring:
        reasons.append("Recurring commission language detected")
        known_fields += 1

    tracking_score = 100.0 if tracking_ready else 30.0
    if tracking_ready:
        reasons.append("Tracking/apply link available")
        known_fields += 1

    score = round(
        monetization * 0.38
        + cookie_score * 0.14
        + recurring_score * 0.14
        + tracking_score * 0.22
        + (source_quality * 100.0) * 0.12,
        2,
    )
    confidence = round(min(0.98, 0.35 + known_fields * 0.11 + source_quality * 0.18), 2)
    return score, reasons, confidence


def _parse_percent(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", value)
    if not match:
        return None
    number = float(match.group(1))
    return number if 0 < number <= 100 else None


def _matches_keywords(keywords: str | None, program: impact.ImpactProgram) -> bool:
    if not keywords:
        return True
    terms = [term.lower() for term in re.findall(r"[\w-]+", keywords) if len(term) >= 2]
    haystack = " ".join(
        filter(
            None,
            (
                program.advertiser_name,
                program.campaign_name,
                program.campaign_description,
                program.advertiser_url,
            ),
        )
    ).lower()
    return any(term in haystack for term in terms)


def _domain_name(url: str) -> str:
    from urllib.parse import urlparse

    host = urlparse(url).hostname or url
    return host.removeprefix("www.")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
