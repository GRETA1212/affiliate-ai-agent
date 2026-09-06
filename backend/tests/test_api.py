from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_score_opportunity() -> None:
    payload = {
        "product_name": "Example VPS",
        "network": "example",
        "demand": 90,
        "buyer_intent": 95,
        "trend": 80,
        "competition": 40,
        "commission_attractiveness": 85,
        "network_epc_signal": 75,
    }
    response = client.post("/api/v1/score", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 83.2
    assert body["rating"] == "high"


def test_forecast() -> None:
    response = client.post(
        "/api/v1/forecast",
        json={
            "monthly_views": 10000,
            "click_through_rate": 0.05,
            "conversion_rate": 0.03,
            "commission_per_conversion": 40,
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "expected_clicks": 500.0,
        "expected_conversions": 15.0,
        "expected_revenue": 600.0,
        "expected_epc": 1.2,
    }


def test_campaign_is_help_first() -> None:
    response = client.post(
        "/api/v1/campaign",
        json={
            "product_name": "Example VPS",
            "audience": "beginner developers",
            "problem": "deploying a Python app cheaply",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "solve" in body["angle"].lower()
    assert "affiliate links" in body["disclosure"].lower()
