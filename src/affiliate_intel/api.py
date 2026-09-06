from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from .db import Repository

DB_PATH = Path(os.getenv("AFFILIATE_INTEL_DB", "affiliate_intel.db"))
repo = Repository(DB_PATH)
repo.init()

app = FastAPI(title="Affiliate Intelligence Engine", version="0.2.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/offers")
def offers() -> list[dict]:
    return repo.list_programs()


@app.get("/offers/{slug}")
def offer(slug: str) -> dict:
    program = repo.get_program(slug)
    if not program:
        raise HTTPException(status_code=404, detail="Offer not found")
    return program


@app.get("/campaigns")
def campaigns() -> list[dict]:
    return repo.list_campaigns()


@app.get("/analytics/summary")
def analytics_summary() -> dict:
    summary = repo.analytics_summary()
    summary["recent_clicks"] = repo.recent_clicks(limit=10)
    return summary


@app.get("/analytics/offers")
def analytics_offers() -> list[dict]:
    return repo.analytics_offers()


@app.get("/go/{offer_slug}")
def track_and_redirect(
    offer_slug: str,
    request: Request,
    campaign_id: int | None = Query(default=None),
    utm_source: str | None = Query(default=None),
    utm_medium: str | None = Query(default=None),
    utm_campaign: str | None = Query(default=None),
    utm_content: str | None = Query(default=None),
) -> RedirectResponse:
    program = repo.get_program(offer_slug)
    if not program:
        raise HTTPException(status_code=404, detail="Offer not found")
    if program["verification_status"] != "verified":
        raise HTTPException(status_code=409, detail="Offer is not verified for live traffic")
    destination = program.get("affiliate_url")
    if not destination:
        raise HTTPException(status_code=409, detail="Affiliate URL is not configured")

    link = repo.ensure_affiliate_link(offer_slug, destination, campaign_id)
    click_id = repo.record_click(
        link["id"],
        referrer=request.headers.get("referer"),
        visitor_key=request.headers.get("user-agent"),
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
    )

    response = RedirectResponse(url=destination, status_code=302)
    response.headers["X-Affiliate-Click-ID"] = click_id
    return response
