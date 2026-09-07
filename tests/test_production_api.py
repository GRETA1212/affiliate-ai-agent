from fastapi.testclient import TestClient

from affiliate_intel import production_api


client = TestClient(production_api.app)


def test_health_reports_storage_configuration(monkeypatch):
    monkeypatch.setattr(production_api, "DATABASE_URL", None)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "storage_configured": False}


def test_unknown_offer_returns_to_landing_page():
    response = client.get("/go/not-a-real-offer", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_taskade_redirect_is_fail_open_without_database(monkeypatch):
    monkeypatch.setattr(production_api, "DATABASE_URL", None)
    response = client.get(
        "/go/taskade?utm_source=test&utm_medium=ci&utm_campaign=production-route",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == production_api.TASKADE_AFFILIATE_URL
    assert response.headers["x-affiliate-tracked"] == "0"
    assert response.headers["x-affiliate-click-id"]
