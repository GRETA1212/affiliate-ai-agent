from __future__ import annotations

import os
import uuid

import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="Affiliate Intelligence Engine", version="0.3.0")


def connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required in production")
    return psycopg.connect(DATABASE_URL)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "storage": "postgres"}


@app.get("/", response_class=HTMLResponse)
def landing() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Taskade AI Agents Review — Affiliate Intelligence Lab</title>
<style>body{font-family:system-ui,sans-serif;max-width:820px;margin:0 auto;padding:40px 20px;line-height:1.65;color:#161616}h1{font-size:clamp(2rem,6vw,3.6rem);line-height:1.05}h2{margin-top:2.2rem}.tag{font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:.8rem}.cta{display:inline-block;background:#161616;color:#fff;padding:14px 20px;border-radius:10px;text-decoration:none;font-weight:700}.note{background:#f3f3f3;padding:16px;border-radius:10px}footer{margin-top:48px;font-size:.9rem;color:#555}</style></head>
<body><div class="tag">Affiliate Intelligence Lab · 2026 test</div>
<h1>Can Taskade AI agents simplify a small-business workflow?</h1>
<p>We are testing Taskade as an AI workspace for turning incoming leads into organized follow-up work. The goal is not to claim that AI replaces judgment; it is to see whether one workspace can reduce repetitive coordination.</p>
<h2>The workflow we are testing</h2><ol><li>Capture a new prospect or request.</li><li>Classify what the prospect needs.</li><li>Create a follow-up task.</li><li>Draft a response.</li><li>Move the work into a simple pipeline for human review.</li></ol>
<h2>Where Taskade looks useful</h2><p>Taskade combines projects, automations and AI agents in one workspace. That makes it interesting for freelancers, consultants and small teams that otherwise stitch together several separate tools.</p>
<h2>Where we would keep a human involved</h2><p>Important customer communication, commercial commitments and final decisions should still be reviewed by a person. Automation is most useful for repetitive preparation and organization.</p>
<div class="note"><strong>Affiliate disclosure:</strong> This page contains an affiliate link. If you purchase through it, we may earn a commission at no additional cost to you. Our tracking measures which campaigns generate useful clicks and paid conversions.</div>
<p><a class="cta" href="/go/taskade?utm_source=website&utm_medium=affiliate&utm_campaign=taskade-small-business&utm_content=review-main">Try Taskade →</a></p>
<footer>Affiliate Intelligence Lab · Practical AI-tool tests for real workflows.</footer></body></html>"""


@app.get("/go/{offer_slug}")
def track_and_redirect(
    offer_slug: str,
    request: Request,
    campaign_id: str | None = Query(default=None),
    utm_source: str | None = Query(default=None),
    utm_medium: str | None = Query(default=None),
    utm_campaign: str | None = Query(default=None),
    utm_content: str | None = Query(default=None),
) -> RedirectResponse:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT affiliate_url, verification_status FROM affiliate_offers WHERE slug = %s",
                (offer_slug,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Offer not found")
            affiliate_url, verification_status = row
            if verification_status != "verified":
                raise HTTPException(status_code=409, detail="Offer is not verified for live traffic")

            click_id = uuid.uuid4()
            cur.execute(
                """INSERT INTO affiliate_clicks
                (click_id, offer_slug, campaign_id, referrer, user_agent, utm_source, utm_medium, utm_campaign, utm_content)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    click_id,
                    offer_slug,
                    campaign_id,
                    request.headers.get("referer"),
                    request.headers.get("user-agent"),
                    utm_source,
                    utm_medium,
                    utm_campaign,
                    utm_content,
                ),
            )
        conn.commit()

    response = RedirectResponse(url=affiliate_url, status_code=302)
    response.headers["X-Affiliate-Click-ID"] = str(click_id)
    return response
