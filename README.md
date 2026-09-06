# Affiliate Intelligence Engine

A small, auditable foundation for discovering, scoring, tracking, and optimizing affiliate opportunities.

## Current capabilities

- SQLite persistence for affiliate programs, opportunity scores, campaigns, content assets, links, clicks, conversions, commissions, and daily metrics
- deterministic opportunity scoring with verification penalties
- JSON candidate ingestion and ranking
- FastAPI revenue-tracking API
- `/go/{offer_slug}` affiliate redirect with unique click IDs and UTM persistence
- live-traffic guard that blocks unverified offers or offers without a configured real affiliate URL
- analytics for CTR, conversion rate, EPC, RPM, revenue, and recent clicks
- launch seed for the first verified offers

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

## Initialize the database

```bash
affiliate-intel --db data/affiliate_intel.db init-db
```

## Load the verified launch offers

```bash
affiliate-intel --db data/affiliate_intel.db ingest data/launch_offers.json
```

The launch seed currently contains Taskade, Scalenut, and Writesonic terms verified against their official affiliate documentation on 2026-09-06. `affiliate_url` is deliberately `null` until the user is actually accepted/registered and copies the real referral URL. Never fabricate an affiliate URL.

## Score candidates

```bash
affiliate-intel score-file data/launch_offers.json
```

## Run the API

```bash
uvicorn affiliate_intel.api:app --reload --port 8000
```

Useful endpoints:

- `GET /health`
- `GET /offers`
- `GET /offers/{slug}`
- `GET /campaigns`
- `GET /analytics/summary`
- `GET /analytics/offers`
- `GET /go/{offer_slug}`

Example tracked route after a real affiliate URL has been configured:

```text
/go/taskade?utm_source=tiktok&utm_medium=organic-social&utm_campaign=taskade-small-business&utm_content=video-01
```

## First launch campaign

See [`docs/launch-campaign-01.md`](docs/launch-campaign-01.md).

The launch order is:

1. create the Taskade partner account and obtain the real referral URL
2. configure that URL in the local database
3. publish the Taskade workflow test/review and short-form content
4. route all affiliate traffic through `/go/taskade`
5. measure real clicks, conversions, EPC, and RPM
6. apply to Writesonic and Scalenut with truthful promotion links and scale the best-performing economics

## Safety / integrity rules

- official-source verification is separate from discovery
- unknown financial terms stay unverified
- stale/unverified programs are discounted by the scorer
- rejected programs score zero
- live redirects require `verification_status=verified`
- live redirects require a real configured `affiliate_url`
- do not self-refer or invent audience/traffic/performance claims
- affiliate disclosures should be visible near commercial CTAs

## Tests

```bash
pytest
```

The tracking test suite covers redirect tracking, UTM persistence, invalid offers, unverified-offer blocking, and analytics formulas.
