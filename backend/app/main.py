from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.connectors.cj import (
    CJAPIError,
    CJConfigurationError,
    CJLinkSearchQuery,
    CJLinkSearchResponse,
)
from app.connectors.cj import search_links as search_cj_links
from app.connectors.cj import status as cj_status
from app.connectors.direct_program import (
    DirectProgramScan,
    DirectProgramScanError,
    DirectProgramScanRequest,
    scan_program,
)
from app.connectors.impact import (
    ImpactAdListResponse,
    ImpactAPIError,
    ImpactConfigurationError,
    ImpactProgramListResponse,
    list_ads as list_impact_ads,
    list_programs as list_impact_programs,
    status as impact_status,
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

app = FastAPI(title="Affiliate AI Agent", version="0.3.0")
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
    connector = cj_status()
    return {
        "name": connector.name,
        "configured": connector.configured,
        "note": connector.note,
    }


@app.get("/api/v1/connectors/impact/status")
def get_impact_status() -> dict[str, str | bool]:
    connector = impact_status()
    return {
        "name": connector.name,
        "configured": connector.configured,
        "note": connector.note,
    }


@app.get("/api/v1/cj/links", response_model=CJLinkSearchResponse)
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
) -> CJLinkSearchResponse:
    query = CJLinkSearchQuery(
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
        return search_cj_links(query)
    except CJConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CJAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/impact/programs", response_model=ImpactProgramListResponse)
def impact_programs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
) -> ImpactProgramListResponse:
    try:
        return list_impact_programs(page=page, page_size=page_size)
    except ImpactConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ImpactAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/impact/ads", response_model=ImpactAdListResponse)
def impact_ads(
    campaign_id: str | None = Query(default=None, max_length=100),
    ad_type: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
) -> ImpactAdListResponse:
    try:
        return list_impact_ads(
            campaign_id=campaign_id,
            ad_type=ad_type,
            page=page,
            page_size=page_size,
        )
    except ImpactConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ImpactAPIError as exc:
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
