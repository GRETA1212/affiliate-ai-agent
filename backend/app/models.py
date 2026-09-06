from typing import Annotated

from pydantic import BaseModel, Field

Score = Annotated[float, Field(ge=0, le=100)]


class OfferSignals(BaseModel):
    product_name: str
    network: str | None = None
    demand: Score
    buyer_intent: Score
    trend: Score
    competition: Score
    commission_attractiveness: Score
    network_epc_signal: Score


class ScoreBreakdown(BaseModel):
    demand: float
    buyer_intent: float
    trend: float
    inverse_competition: float
    commission_attractiveness: float
    network_epc_signal: float


class OpportunityResult(BaseModel):
    product_name: str
    network: str | None
    score: float
    rating: str
    breakdown: ScoreBreakdown


class ForecastInput(BaseModel):
    monthly_views: int = Field(ge=0)
    click_through_rate: float = Field(ge=0, le=1)
    conversion_rate: float = Field(ge=0, le=1)
    commission_per_conversion: float = Field(ge=0)


class ForecastResult(BaseModel):
    expected_clicks: float
    expected_conversions: float
    expected_revenue: float
    expected_epc: float


class CampaignRequest(BaseModel):
    product_name: str
    audience: str
    problem: str
    affiliate_url: str | None = None


class CampaignPlan(BaseModel):
    angle: str
    article_titles: list[str]
    video_titles: list[str]
    disclosure: str
    affiliate_url: str | None
