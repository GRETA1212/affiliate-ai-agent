from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from app.services.opportunity_scorer import score_opportunity

app = FastAPI(title="Affiliate AI Agent", version="0.1.0")
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


@app.post("/api/v1/score", response_model=OpportunityResult)
def score(signals: OfferSignals) -> OpportunityResult:
    return score_opportunity(signals)


@app.post("/api/v1/forecast", response_model=ForecastResult)
def forecast(data: ForecastInput) -> ForecastResult:
    return forecast_revenue(data)


@app.post("/api/v1/campaign", response_model=CampaignPlan)
def campaign(request: CampaignRequest) -> CampaignPlan:
    return build_campaign(request)
