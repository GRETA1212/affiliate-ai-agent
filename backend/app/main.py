from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.connectors import cj, impact, youtube
from app.connectors.direct_program import (
    DirectProgramScan,
    DirectProgramScanError,
    DirectProgramScanRequest,
    scan_program,
)
from app.models import (
    CampaignPlan,
    CampaignRequest,
    ForecastInput,
    ForecastResult,
    OfferSignals,
    OpportunityResult,
)
from app.services.content_agent import build_campaign
from app.services.forecast import forecast_revenue
from app.services.opportunity_aggregator import (
    TopOpportunityRequest,
    TopOpportunityResponse,
    find_top_opportunities,
)
from app.services.opportunity_scorer import score_opportunity

app = FastAPI(title="Affiliate AI Agent", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/connectors/cj/status")
def get_cj_status() -> dict[str, str | bool]:
    connector = cj.status()
    return {
        "name": connector.name,
        "configured": connector.configured,
        "note": connector.note,
    }


@app.get("/api/v1/connectors/impact/status")
def get_impact_status() -> dict[str, str | bool]:
    connector = impact.status()
    return {
        "name": connector.name,
        "configured": connector.configured,
        "note": connector.note,
    }


@app.get("/api/v1/connectors/youtube/status")
def get_youtube_status() -> dict[str, str | bool]:
    connector = youtube.status()
    return {
        "name": connector.name,
        "configured": connector.configured,
        "note": connector.note,
    }


@app.get("/api/v1/cj/links", response_model=cj.CJLinkSearchResponse)
def cj_links(
    keywords: str | None = Query(default=None, max_length=200),
    advertiser_ids: str = Query(default="joined", min_length=1, max_length=500),
    category: str | None = Query(default=None, max_length=200),
    link_type: str | None = Query(default=None, max_length=100),
    promotion_type: str | None = Query(default=None, max_length=100),
    targeted_country: str | None = Query(default=None, min_length=2, max_length=2),
    allow_deep_linking: bool | None = Query(default=None),
    page_number: int = Query(default=1, ge=1),
    records_per_page: int = Query(default=25, ge=1, le=100),
) -> cj.CJLinkSearchResponse:
    query = cj.CJLinkSearchQuery(
        keywords=keywords,
        advertiser_ids=advertiser_ids,
        category=category,
        link_type=link_type,
        promotion_type=promotion_type,
        targeted_country=targeted_country,
        allow_deep_linking=allow_deep_linking,
        page_number=page_number,
        records_per_page=records_per_page,
    )
    try:
        return cj.search_links(query)
    except cj.CJConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except cj.CJAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/impact/programs", response_model=impact.ImpactProgramListResponse)
def impact_programs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
) -> impact.ImpactProgramListResponse:
    try:
        return impact.list_programs(page=page, page_size=page_size)
    except impact.ImpactConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except impact.ImpactAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get(
    "/api/v1/impact/programs/{campaign_id}/public-terms",
    response_model=impact.ImpactPublicTerms,
)
def impact_public_terms(campaign_id: str) -> impact.ImpactPublicTerms:
    try:
        return impact.get_public_terms(campaign_id)
    except impact.ImpactConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except impact.ImpactAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/impact/ads", response_model=impact.ImpactAdListResponse)
def impact_ads(
    campaign_id: str | None = Query(default=None, max_length=100),
    ad_type: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
) -> impact.ImpactAdListResponse:
    try:
        return impact.list_ads(
            campaign_id=campaign_id,
            ad_type=ad_type,
            page=page,
            page_size=page_size,
        )
    except impact.ImpactConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except impact.ImpactAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/youtube/market", response_model=youtube.YouTubeMarketSignal)
def youtube_market(
    query: str = Query(min_length=2, max_length=200),
    max_results: int = Query(default=15, ge=5, le=25),
    region_code: str | None = Query(default=None, min_length=2, max_length=2),
    relevance_language: str | None = Query(default=None, min_length=2, max_length=10),
) -> youtube.YouTubeMarketSignal:
    try:
        return youtube.research_market(
            youtube.YouTubeMarketQuery(
                query=query,
                max_results=max_results,
                region_code=region_code,
                relevance_language=relevance_language,
            )
        )
    except youtube.YouTubeConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except youtube.YouTubeAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/v1/direct/scan", response_model=DirectProgramScan)
def direct_scan(request: DirectProgramScanRequest) -> DirectProgramScan:
    try:
        return scan_program(request)
    except DirectProgramScanError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/v1/opportunities/top", response_model=TopOpportunityResponse)
def top_opportunities(request: TopOpportunityRequest) -> TopOpportunityResponse:
    return find_top_opportunities(request)


@app.post("/api/v1/score", response_model=OpportunityResult)
def score(signals: OfferSignals) -> OpportunityResult:
    return score_opportunity(signals)


@app.post("/api/v1/forecast", response_model=ForecastResult)
def forecast(data: ForecastInput) -> ForecastResult:
    return forecast_revenue(data)


@app.post("/api/v1/campaign", response_model=CampaignPlan)
def campaign(request: CampaignRequest) -> CampaignPlan:
    return build_campaign(request)
