from app.models import ForecastInput, ForecastResult


def forecast_revenue(data: ForecastInput) -> ForecastResult:
    clicks = data.monthly_views * data.click_through_rate
    conversions = clicks * data.conversion_rate
    revenue = conversions * data.commission_per_conversion
    epc = revenue / clicks if clicks else 0.0
    return ForecastResult(
        expected_clicks=round(clicks, 2),
        expected_conversions=round(conversions, 2),
        expected_revenue=round(revenue, 2),
        expected_epc=round(epc, 4),
    )
