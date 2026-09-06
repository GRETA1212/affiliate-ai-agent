from pathlib import Path

from fastapi.testclient import TestClient

from affiliate_intel.db import Repository
from affiliate_intel.models import AffiliateProgram


def build_client(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("AFFILIATE_INTEL_DB", str(db_path))

    import importlib
    import affiliate_intel.api as api

    importlib.reload(api)
    return TestClient(api.app), api.repo


def seed_verified_offer(repo: Repository) -> None:
    repo.upsert_program(
        AffiliateProgram(
            slug="demo-ai",
            name="Demo AI",
            product_url="https://example.com",
            affiliate_url="https://example.com/?ref=test123",
            commission_type="recurring",
            commission_rate_pct=30,
            recurring_months=12,
            cookie_days=90,
            verification_status="verified",
        )
    )


def test_redirect_records_click_and_utm(tmp_path, monkeypatch):
    client, repo = build_client(tmp_path, monkeypatch)
    seed_verified_offer(repo)

    response = client.get(
        "/go/demo-ai?utm_source=tiktok&utm_medium=social&utm_campaign=ai-tools&utm_content=hook-a",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/?ref=test123"
    assert response.headers["x-affiliate-click-id"]

    clicks = repo.recent_clicks()
    assert len(clicks) == 1
    assert clicks[0]["utm_source"] == "tiktok"
    assert clicks[0]["utm_medium"] == "social"
    assert clicks[0]["utm_campaign"] == "ai-tools"
    assert clicks[0]["utm_content"] == "hook-a"


def test_invalid_offer_returns_404(tmp_path, monkeypatch):
    client, _ = build_client(tmp_path, monkeypatch)
    response = client.get("/go/missing", follow_redirects=False)
    assert response.status_code == 404


def test_unverified_offer_cannot_receive_live_traffic(tmp_path, monkeypatch):
    client, repo = build_client(tmp_path, monkeypatch)
    repo.upsert_program(
        AffiliateProgram(
            slug="unverified-ai",
            name="Unverified AI",
            product_url="https://example.org",
            affiliate_url="https://example.org/?ref=test",
            commission_type="recurring",
            commission_rate_pct=50,
            verification_status="unverified",
        )
    )

    response = client.get("/go/unverified-ai", follow_redirects=False)
    assert response.status_code == 409
    assert repo.recent_clicks() == []


def test_summary_calculates_epc_conversion_rate_ctr_and_rpm(tmp_path, monkeypatch):
    client, repo = build_client(tmp_path, monkeypatch)
    seed_verified_offer(repo)
    campaign_id = repo.create_campaign("demo-ai", "AI tools launch", "tiktok")
    link = repo.ensure_affiliate_link("demo-ai", "https://example.com/?ref=test123", campaign_id)
    repo.record_click(link["id"])
    repo.record_click(link["id"])

    with repo.connect() as con:
        conversion_id = con.execute(
            "INSERT INTO conversions (affiliate_link_id, conversion_type, revenue) VALUES (?, 'purchase', 100)",
            (link["id"],),
        ).lastrowid
        con.execute(
            "INSERT INTO commissions (conversion_id, program_slug, amount, currency, status) VALUES (?, 'demo-ai', 40, 'EUR', 'approved')",
            (conversion_id,),
        )
        con.execute(
            "INSERT INTO daily_metrics (day, program_slug, impressions, clicks, purchases, commission) VALUES ('2026-09-06', 'demo-ai', 1000, 2, 1, 40)"
        )

    response = client.get("/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["clicks"] == 2
    assert data["conversions"] == 1
    assert data["revenue"] == 40.0
    assert data["epc"] == 20.0
    assert data["conversion_rate"] == 0.5
    assert data["ctr"] == 0.002
    assert data["rpm"] == 40.0
