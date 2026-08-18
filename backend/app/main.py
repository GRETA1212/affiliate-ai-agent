from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

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
from app.services import automation_loop as automation
from app.services import business_controller as business
from app.services import campaign_workspace as workspace
from app.services import network_sync as sync_service
from app.services import performance_advisor as advisor
from app.services.content_agent import build_campaign
from app.services.forecast import forecast_revenue
from app.services.opportunity_aggregator import (
    TopOpportunityRequest,
    TopOpportunityResponse,
    find_top_opportunities,
)
from app.services.opportunity_scorer import score_opportunity

app = FastAPI(title="Affiliate AI Agent", version="1.0.0")
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


@app.get("/api/v1/connectors/cj/commissions/status")
def get_cj_commission_status() -> dict[str, str | bool]:
    connector = cj.commission_status()
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


@app.get("/api/v1/workspace/summary", response_model=workspace.WorkspaceSummary)
def get_workspace_summary() -> workspace.WorkspaceSummary:
    return workspace.workspace_summary()


@app.post(
    "/api/v1/workspace/campaigns",
    response_model=workspace.CampaignDetail,
    status_code=201,
)
def create_workspace_campaign(data: workspace.CampaignCreate) -> workspace.CampaignDetail:
    try:
        return workspace.create_campaign(data)
    except workspace.WorkspaceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/v1/workspace/campaigns", response_model=list[workspace.CampaignDetail])
def list_workspace_campaigns(
    status: workspace.CampaignStatus | None = None,
) -> list[workspace.CampaignDetail]:
    return workspace.list_campaigns(status)


@app.get(
    "/api/v1/workspace/campaigns/{campaign_id}",
    response_model=workspace.CampaignDetail,
)
def get_workspace_campaign(campaign_id: str) -> workspace.CampaignDetail:
    try:
        return workspace.get_campaign(campaign_id)
    except workspace.WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch(
    "/api/v1/workspace/campaigns/{campaign_id}",
    response_model=workspace.CampaignDetail,
)
def patch_workspace_campaign(
    campaign_id: str,
    data: workspace.CampaignUpdate,
) -> workspace.CampaignDetail:
    try:
        return workspace.update_campaign(campaign_id, data)
    except workspace.WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get(
    "/api/v1/workspace/campaigns/{campaign_id}/metrics",
    response_model=workspace.CampaignMetrics,
)
def get_workspace_campaign_metrics(campaign_id: str) -> workspace.CampaignMetrics:
    try:
        return workspace.campaign_metrics(campaign_id)
    except workspace.WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/workspace/campaigns/{campaign_id}/conversions",
    response_model=workspace.ConversionRecord,
    status_code=201,
)
def create_workspace_conversion(
    campaign_id: str,
    data: workspace.ConversionCreate,
) -> workspace.ConversionRecord:
    try:
        return workspace.add_conversion(campaign_id, data)
    except workspace.WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except workspace.WorkspaceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get(
    "/api/v1/workspace/campaigns/{campaign_id}/conversions",
    response_model=list[workspace.ConversionRecord],
)
def get_workspace_conversions(campaign_id: str) -> list[workspace.ConversionRecord]:
    try:
        return workspace.list_conversions(campaign_id)
    except workspace.WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch(
    "/api/v1/workspace/conversions/{conversion_id}",
    response_model=workspace.ConversionRecord,
)
def patch_workspace_conversion(
    conversion_id: str,
    data: workspace.ConversionUpdate,
) -> workspace.ConversionRecord:
    try:
        return workspace.update_conversion(conversion_id, data)
    except workspace.WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put(
    "/api/v1/workspace/campaigns/{campaign_id}/binding",
    response_model=sync_service.CampaignBinding,
)
def put_campaign_binding(
    campaign_id: str,
    data: sync_service.CampaignBindingRequest,
) -> sync_service.CampaignBinding:
    try:
        return sync_service.bind_campaign(campaign_id, data)
    except sync_service.SyncNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except sync_service.SyncConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get(
    "/api/v1/workspace/campaigns/{campaign_id}/binding",
    response_model=sync_service.CampaignBinding,
)
def get_campaign_binding(campaign_id: str) -> sync_service.CampaignBinding:
    try:
        return sync_service.get_binding(campaign_id)
    except sync_service.SyncNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/workspace/campaigns/{campaign_id}/impact-tracking-link",
    response_model=sync_service.ImpactTrackingLinkResult,
)
def create_impact_tracking_link(
    campaign_id: str,
    data: sync_service.ImpactTrackingLinkRequest,
) -> sync_service.ImpactTrackingLinkResult:
    try:
        return sync_service.create_tagged_impact_link(campaign_id, data)
    except sync_service.SyncNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except sync_service.SyncConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except impact.ImpactConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except impact.ImpactAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/v1/workspace/sync", response_model=sync_service.SyncResponse)
def sync_workspace(data: sync_service.SyncRequest) -> sync_service.SyncResponse:
    return sync_service.sync_networks(data)


@app.get(
    "/api/v1/workspace/unmatched",
    response_model=list[sync_service.NetworkEventRecord],
)
def get_unmatched_events(
    limit: int = Query(default=100, ge=1, le=500),
) -> list[sync_service.NetworkEventRecord]:
    return sync_service.list_unmatched_events(limit)


@app.post(
    "/api/v1/workspace/network-events/{event_id}/assign/{campaign_id}",
    response_model=sync_service.NetworkEventRecord,
)
def assign_network_event(
    event_id: str,
    campaign_id: str,
) -> sync_service.NetworkEventRecord:
    try:
        return sync_service.assign_event(event_id, campaign_id)
    except sync_service.SyncNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get(
    "/api/v1/workspace/sync/status",
    response_model=list[sync_service.SyncStateRecord],
)
def get_sync_status() -> list[sync_service.SyncStateRecord]:
    return sync_service.list_sync_state()


@app.get(
    "/api/v1/performance/recommendations",
    response_model=advisor.AdvisorResponse,
)
def performance_recommendations(
    min_sample_clicks: int = Query(default=50, ge=10, le=10000),
    stop_clicks: int = Query(default=150, ge=25, le=50000),
    low_conversion_rate: float = Query(default=0.005, ge=0, le=1),
    healthy_conversion_rate: float = Query(default=0.02, ge=0, le=1),
    winner_epc_multiplier: float = Query(default=1.25, ge=1, le=10),
    loser_epc_multiplier: float = Query(default=0.5, ge=0, le=1),
) -> advisor.AdvisorResponse:
    settings = advisor.AdvisorSettings(
        min_sample_clicks=min_sample_clicks,
        stop_clicks=stop_clicks,
        low_conversion_rate=low_conversion_rate,
        healthy_conversion_rate=healthy_conversion_rate,
        winner_epc_multiplier=winner_epc_multiplier,
        loser_epc_multiplier=loser_epc_multiplier,
    )
    return advisor.analyze_portfolio(settings)


@app.get("/api/v1/business/profit", response_model=business.ProfitSummary)
def business_profit() -> business.ProfitSummary:
    return business.profit_summary()


@app.post("/api/v1/business/expenses", status_code=201)
def create_business_expense(data: business.ExpenseCreate) -> dict[str, str]:
    try:
        return {"id": business.record_expense(data)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/business/next-actions", response_model=list[business.NextAction])
def business_next_actions(limit: int = Query(default=10, ge=1, le=100)) -> list[business.NextAction]:
    return business.next_actions(limit=limit)


@app.post("/api/v1/business/plan", response_model=automation.AutomationRun)
def business_plan(limit: int = Query(default=10, ge=1, le=100)) -> automation.AutomationRun:
    return automation.plan_work(limit=limit)


@app.post("/api/v1/business/jobs", status_code=201)
def create_business_job(data: business.ContentJobCreate) -> dict[str, str]:
    return {"id": business.enqueue_content_job(data)}


@app.post("/api/v1/business/jobs/claim")
def claim_business_job() -> dict | None:
    return business.claim_next_job()


@app.post("/api/v1/business/experiments", status_code=201)
def create_business_experiment(data: business.ExperimentCreate) -> dict[str, str]:
    try:
        return {"id": business.create_experiment(data)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/business/experiments/{experiment_id}/observe")
def observe_business_experiment(
    experiment_id: str,
    variant: str = Query(pattern="^[ab]$"),
    converted: bool = Query(default=False),
) -> dict[str, str]:
    try:
        business.record_experiment_observation(experiment_id, variant, converted)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "recorded"}


@app.post("/api/v1/business/experiments/{experiment_id}/finish")
def finish_business_experiment(
    experiment_id: str,
    minimum_impressions_per_variant: int = Query(default=50, ge=10, le=100000),
) -> dict[str, str]:
    try:
        winner = business.finish_experiment(experiment_id, minimum_impressions_per_variant)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"winner": winner}


@app.get("/go/{slug}", include_in_schema=False)
def tracked_redirect(
    slug: str,
    request: Request,
    source: str | None = Query(default=None, max_length=200),
    medium: str | None = Query(default=None, max_length=200),
    content: str | None = Query(default=None, max_length=200),
) -> RedirectResponse:
    try:
        target = workspace.record_click(
            slug,
            source=source,
            medium=medium,
            content=content,
            referrer=request.headers.get("referer"),
            user_agent=request.headers.get("user-agent"),
        )
    except workspace.WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except workspace.WorkspaceInactive as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RedirectResponse(target, status_code=302)
