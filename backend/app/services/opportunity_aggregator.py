import math
import re

from pydantic import BaseModel, Field, HttpUrl

from app.connectors import cj, impact, youtube
from app.connectors.direct_program import (
    DirectProgramScan,
    DirectProgramScanError,
    DirectProgramScanRequest,
    scan_program,
)
from app.services.verified_catalog import VerifiedAffiliateProgram, search_verified_programs


class TopOpportunityRequest(BaseModel):
    keywords: str | None = Field(default=None, max_length=200)
    direct_urls: list[HttpUrl] = Field(default_factory=list, max_length=10)
    include_cj: bool = True
    include_impact: bool = True
    include_verified_catalog: bool = True
    enrich_impact_terms: bool = True
    impact_terms_limit: int = Field(default=12, ge=0, le=30)
    include_youtube: bool = True
    youtube_probe_count: int = Field(default=3, ge=0, le=5)
    limit: int = Field(default=10, ge=1, le=50)


class RankedAffiliateOpportunity(BaseModel):
    source: str
    name: str
    advertiser: str | None
    program_url: str | None
    tracking_url: str | None
    network_hint: str | None = None
    commission_text: str | None
    commission_percent: float | None
    fixed_payout_amount: float | None = None
    fixed_payout_currency: str | None = None
    epc_per_click: float | None
    cookie_days: int | None
    recurring: bool
    verified_at: str | None = None
    commercial_readiness_score: float
    opportunity_score: float
    market_interest_score: float | None = None
    market_competition_score: float | None = None
    confidence: float
    reasons: list[str]


class TopOpportunityResponse(BaseModel):
    keywords: str | None
    opportunities: list[RankedAffiliateOpportunity]
    warnings: list[str]
    scoring_note: str = (
        "Opportunity score starts with commercial readiness from commission, EPC, attribution, "
        "recurrence and tracking evidence. When YouTube is configured, a small market-interest "
        "and competition adjustment is applied. It is a prioritization heuristic, not a profit guarantee."
    )


def find_top_opportunities(request: TopOpportunityRequest) -> TopOpportunityResponse:
    opportunities: list[RankedAffiliateOpportunity] = []
    warnings: list[str] = []

    if request.include_verified_catalog:
        opportunities.extend(_from_verified(item) for item in search_verified_programs(request.keywords))

    if request.include_cj:
        if cj.status().configured:
            try:
                result = cj.search_links(
                    cj.CJLinkSearchQuery(
                        keywords=request.keywords,
                        advertiser_ids="joined",
                        records_per_page=min(100, max(25, request.limit * 3)),
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
                matches = [
                    program
                    for program in result.programs
                    if _matches_keywords(request.keywords, program)
                ]
                for index, program in enumerate(matches[: max(request.limit * 2, 20)]):
                    terms: impact.ImpactPublicTerms | None = None
                    if (
                        request.enrich_impact_terms
                        and index < request.impact_terms_limit
                        and program.campaign_id
                    ):
                        try:
                            terms = impact.get_public_terms(program.campaign_id)
                        except impact.ImpactAPIError as exc:
                            warnings.append(
                                f"Impact terms {program.campaign_name or program.campaign_id}: {exc}"
                            )
                    opportunities.append(_from_impact(program, terms))
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

    opportunities = _dedupe_opportunities(opportunities)
    opportunities.sort(key=_sort_key, reverse=True)

    if request.include_youtube and request.youtube_probe_count > 0 and request.keywords:
        if youtube.status().configured:
            _enrich_with_youtube(opportunities, request, warnings)
        else:
            warnings.append("YouTube is not configured; skipped live market-interest research.")

    opportunities.sort(key=_sort_key, reverse=True)
    return TopOpportunityResponse(
        keywords=request.keywords,
        opportunities=opportunities[: request.limit],
        warnings=_dedupe(warnings),
    )


def _from_cj(link: cj.CJLink) -> RankedAffiliateOpportunity:
    commission_percent = _parse_percent(link.sale_commission)
    epc = link.three_month_epc_per_click or link.seven_day_epc_per_click
    score, reasons, confidence = _score(
        commission_percent=commission_percent,
        fixed_payout_amount=_parse_money(link.lead_commission or link.click_commission),
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
        network_hint="cj",
        commission_text=link.sale_commission or link.lead_commission or link.click_commission,
        commission_percent=commission_percent,
        fixed_payout_amount=_parse_money(link.lead_commission or link.click_commission),
        fixed_payout_currency=None,
        epc_per_click=epc,
        cookie_days=None,
        recurring=False,
        commercial_readiness_score=score,
        opportunity_score=score,
        confidence=confidence,
        reasons=reasons,
    )


def _from_impact(
    program: impact.ImpactProgram,
    terms: impact.ImpactPublicTerms | None,
) -> RankedAffiliateOpportunity:
    metrics = _impact_metrics(terms)
    score, reasons, confidence = _score(
        commission_percent=metrics["commission_percent"],
        fixed_payout_amount=metrics["fixed_payout_amount"],
        epc_per_click=None,
        cookie_days=metrics["cookie_days"],
        recurring=False,
        tracking_ready=bool(program.tracking_link),
        source_quality=0.98 if terms else 0.9,
    )
    if program.contract_status and program.contract_status.lower() == "active":
        score = min(100.0, round(score + 6.0, 2))
        reasons.append("Active Impact contract")
    if terms and terms.payout_terms:
        reasons.append("Impact public payout terms loaded live")
    return RankedAffiliateOpportunity(
        source="impact",
        name=program.campaign_name or program.advertiser_name or "Impact program",
        advertiser=program.advertiser_name,
        program_url=program.campaign_url or program.advertiser_url,
        tracking_url=program.tracking_link,
        network_hint="impact",
        commission_text=metrics["commission_text"],
        commission_percent=metrics["commission_percent"],
        fixed_payout_amount=metrics["fixed_payout_amount"],
        fixed_payout_currency=metrics["fixed_payout_currency"],
        epc_per_click=None,
        cookie_days=metrics["cookie_days"],
        recurring=False,
        commercial_readiness_score=score,
        opportunity_score=score,
        confidence=confidence,
        reasons=reasons,
    )


def _from_direct(scanned: DirectProgramScan) -> RankedAffiliateOpportunity:
    score, reasons, confidence = _score(
        commission_percent=scanned.commission_percent,
        fixed_payout_amount=None,
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
        network_hint=scanned.network_hint,
        commission_text=scanned.commission_text,
        commission_percent=scanned.commission_percent,
        fixed_payout_amount=None,
        fixed_payout_currency=None,
        epc_per_click=None,
        cookie_days=scanned.cookie_days,
        recurring=scanned.recurring,
        commercial_readiness_score=score,
        opportunity_score=score,
        confidence=min(confidence, scanned.confidence),
        reasons=_dedupe(reasons),
    )


def _from_verified(program: VerifiedAffiliateProgram) -> RankedAffiliateOpportunity:
    score, reasons, confidence = _score(
        commission_percent=program.commission_percent,
        fixed_payout_amount=program.fixed_payout_amount,
        epc_per_click=None,
        cookie_days=program.cookie_days,
        recurring=program.recurring,
        tracking_ready=bool(program.application_url or program.program_url),
        source_quality=0.93,
    )
    reasons.append(f"Verified against an official program page on {program.verified_at.isoformat()}")
    reasons.extend(program.notes)
    if program.recurring_months:
        reasons.append(f"Published recurring window: {program.recurring_months} months")
    return RankedAffiliateOpportunity(
        source="verified-direct",
        name=program.name,
        advertiser=program.advertiser,
        program_url=program.program_url,
        tracking_url=None,
        network_hint=program.network,
        commission_text=program.commission_text,
        commission_percent=program.commission_percent,
        fixed_payout_amount=program.fixed_payout_amount,
        fixed_payout_currency=program.fixed_payout_currency,
        epc_per_click=None,
        cookie_days=program.cookie_days,
        recurring=program.recurring,
        verified_at=program.verified_at.isoformat(),
        commercial_readiness_score=score,
        opportunity_score=score,
        confidence=confidence,
        reasons=_dedupe(reasons),
    )


def _impact_metrics(terms: impact.ImpactPublicTerms | None) -> dict[str, object]:
    if terms is None:
        return {
            "commission_percent": None,
            "fixed_payout_amount": None,
            "fixed_payout_currency": None,
            "cookie_days": None,
            "commission_text": None,
        }

    percentages: list[float] = []
    fixed_amounts: list[tuple[float, str | None]] = []
    referral_days: list[int] = []
    summaries: list[str] = []
    for term in terms.payout_terms:
        for value in (
            term.payout_percentage,
            term.payout_percentage_lower_limit,
            term.payout_percentage_upper_limit,
        ):
            if value is not None and value > 0:
                percentages.append(value)
        for value in (
            term.payout_amount,
            term.payout_amount_lower_limit,
            term.payout_amount_upper_limit,
        ):
            if value is not None and value > 0:
                fixed_amounts.append((value, term.payout_currency))
        days = _referral_days(term.referral_period, term.referral_period_unit)
        if days is not None:
            referral_days.append(days)

        label = term.tracker_name or term.tracker_type or "action"
        if term.payout_percentage:
            summaries.append(f"{term.payout_percentage:g}% {label}")
        elif term.payout_amount:
            currency = f" {term.payout_currency}" if term.payout_currency else ""
            summaries.append(f"{term.payout_amount:g}{currency} {label}")

    best_fixed = max(fixed_amounts, default=(None, None), key=lambda item: item[0] or 0)
    return {
        "commission_percent": max(percentages) if percentages else None,
        "fixed_payout_amount": best_fixed[0],
        "fixed_payout_currency": best_fixed[1],
        "cookie_days": max(referral_days) if referral_days else None,
        "commission_text": "; ".join(_dedupe(summaries)) or None,
    }


def _score(
    *,
    commission_percent: float | None,
    fixed_payout_amount: float | None,
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
    if fixed_payout_amount is not None:
        monetization_values.append(min(100.0, fixed_payout_amount / 300.0 * 100.0))
        reasons.append(f"Fixed payout detected: {fixed_payout_amount:g}")
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


def _enrich_with_youtube(
    opportunities: list[RankedAffiliateOpportunity],
    request: TopOpportunityRequest,
    warnings: list[str],
) -> None:
    candidates = opportunities[: request.youtube_probe_count]
    for item in candidates:
        query_text = _youtube_query(item, request.keywords or "")
        try:
            signal = youtube.research_market(
                youtube.YouTubeMarketQuery(query=query_text, max_results=15)
            )
        except (youtube.YouTubeAPIError, youtube.YouTubeConfigurationError) as exc:
            warnings.append(f"YouTube {item.advertiser or item.name}: {exc}")
            continue

        market_delta = (signal.interest_score - 50.0) * 0.12
        market_delta += (50.0 - signal.competition_score) * 0.08
        item.market_interest_score = signal.interest_score
        item.market_competition_score = signal.competition_score
        item.opportunity_score = round(
            max(0.0, min(100.0, item.commercial_readiness_score + market_delta)),
            2,
        )
        item.confidence = min(0.99, round(item.confidence + 0.04, 2))
        item.reasons = _dedupe(
            [
                *item.reasons,
                f"YouTube interest signal: {signal.interest_score:.0f}/100",
                f"YouTube competition signal: {signal.competition_score:.0f}/100",
                *signal.evidence[:2],
            ]
        )


def _dedupe_opportunities(
    opportunities: list[RankedAffiliateOpportunity],
) -> list[RankedAffiliateOpportunity]:
    merged: dict[str, RankedAffiliateOpportunity] = {}
    for item in opportunities:
        key = _opportunity_key(item)
        if key not in merged:
            merged[key] = item
            continue
        merged[key] = _merge_opportunities(merged[key], item)
    return list(merged.values())


def _merge_opportunities(
    first: RankedAffiliateOpportunity,
    second: RankedAffiliateOpportunity,
) -> RankedAffiliateOpportunity:
    primary, secondary = (
        (first, second)
        if _sort_key(first) >= _sort_key(second)
        else (second, first)
    )
    source_parts = _dedupe([*primary.source.split("+"), *secondary.source.split("+")])
    updates = {
        "source": "+".join(source_parts),
        "tracking_url": primary.tracking_url or secondary.tracking_url,
        "network_hint": primary.network_hint or secondary.network_hint,
        "commission_text": primary.commission_text or secondary.commission_text,
        "commission_percent": primary.commission_percent or secondary.commission_percent,
        "fixed_payout_amount": primary.fixed_payout_amount or secondary.fixed_payout_amount,
        "fixed_payout_currency": primary.fixed_payout_currency or secondary.fixed_payout_currency,
        "epc_per_click": primary.epc_per_click or secondary.epc_per_click,
        "cookie_days": primary.cookie_days or secondary.cookie_days,
        "recurring": primary.recurring or secondary.recurring,
        "verified_at": primary.verified_at or secondary.verified_at,
        "confidence": max(primary.confidence, secondary.confidence),
        "reasons": _dedupe([*primary.reasons, *secondary.reasons]),
    }
    if primary.tracking_url or secondary.tracking_url:
        updates["reasons"] = _dedupe([*updates["reasons"], "Live network tracking link available"])
    return primary.model_copy(update=updates)


def _parse_percent(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", value)
    if not match:
        return None
    number = float(match.group(1))
    return number if 0 < number <= 100 else None


def _parse_money(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"(?:[$€£]\s*)?(\d+(?:\.\d+)?)", value)
    if not match:
        return None
    number = float(match.group(1))
    return number if number > 0 else None


def _referral_days(period: int | None, unit: str | None) -> int | None:
    if period is None or period <= 0 or not unit:
        return None
    normalized = unit.strip().upper()
    if normalized == "DAY":
        return period
    if normalized == "HOUR":
        return max(1, math.ceil(period / 24.0))
    return None


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


def _youtube_query(item: RankedAffiliateOpportunity, keywords: str) -> str:
    brand = item.advertiser or item.name
    value = f"{brand} {keywords}".strip()
    return value[:200]


def _opportunity_key(item: RankedAffiliateOpportunity) -> str:
    value = item.advertiser or item.name
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    for suffix in (" affiliate program", " partner program", " affiliates", " affiliate"):
        normalized = normalized.removesuffix(suffix).strip()
    return normalized or item.name.lower()


def _sort_key(item: RankedAffiliateOpportunity) -> tuple[float, float]:
    return item.opportunity_score, item.confidence


def _domain_name(url: str) -> str:
    from urllib.parse import urlparse

    host = urlparse(url).hostname or url
    return host.removeprefix("www.")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
