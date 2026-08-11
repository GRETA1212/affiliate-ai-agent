# Affiliate AI Agent

AI-assisted affiliate opportunity research, campaign tracking, automatic CJ/Impact commission sync, real revenue measurement, and evidence-based campaign recommendations.

## Current MVP — V0.7

The measurable loop is now:

1. **Find opportunities** from the verified AI-affiliate catalog, CJ, Impact, direct affiliate pages, and YouTube market signals.
2. **Create a persistent campaign** with your approved affiliate tracking URL.
3. **Bind the campaign to CJ or Impact** using the advertiser/program ID.
4. **Publish `/go/{slug}`** and record human/bot-aware clicks before redirecting.
5. **Sync CJ commissions and Impact actions** into SQLite.
6. **Reconcile approvals, reversals, and CJ correction deltas** without double-counting.
7. **Calculate real conversion rate and EPC by currency** from approved commissions.
8. **Detect winners, losers, promising tests, and campaigns that still need more data.**
9. **Recommend the next action**: scale, increase the test, hold, optimize, pause/rework, or collect more data.

Opportunity scores and advisor outputs are decision aids, not profit guarantees. Real earnings require approved affiliate accounts, valid tracking links, qualified traffic, conversions, and compliance with program/platform rules.

## Winner / loser advisor

```text
GET /api/v1/performance/recommendations
```

Default decision thresholds are 50 human clicks for a minimum sample, 150 clicks for a hard no-conversion review, 2% healthy test CVR, 0.5% low CVR, 1.25× same-currency peer-median EPC for a relative winner, and 0.5× for a relative weak signal after enough traffic.

The thresholds are query parameters, so they can be tuned without changing code. The advisor returns classification, recommended action, confidence, priority, real clicks, approved/pending conversions, CVR, revenue, EPC, same-currency peer EPC baseline, reasons, next actions, and an EPC leader for each currency.

Campaigns are **never compared across currencies**.

## Persistent database and tracking

Default database:

```text
data/affiliate.db
```

SQLite stores campaigns, clicks, canonical conversions, CJ/Impact campaign bindings, normalized raw network events, and sync state. Raw IP addresses are deliberately not stored. Bot clicks are excluded from human KPIs. Pending and reversed commissions do not count as approved revenue.

Example tracked link:

```text
http://localhost:8000/go/elevenlabs-review
```

Traffic attribution:

```text
/go/elevenlabs-review?source=youtube&medium=video&content=review-1
```

For real traffic, deploy the backend on a public HTTPS domain.

## Automatic CJ + Impact synchronization

Impact actions are matched by exact `SubId1` campaign attribution token, otherwise by one unambiguous bound Impact `ProgramId`. The app can generate a tagged Impact link using the campaign slug as `subId1`.

CJ Commission Detail records are stored as signed events. Corrections are grouped and netted before one canonical campaign conversion is materialized. Ambiguous network events remain unmatched instead of being guessed.

```text
POST /api/v1/workspace/sync
GET  /api/v1/workspace/unmatched
POST /api/v1/workspace/network-events/{event_id}/assign/{campaign_id}
```

## Run locally

Backend:

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000 --env-file ../.env
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and API docs at `http://localhost:8000/docs`.

## Credentials

```text
CJ_API_TOKEN=
CJ_WEBSITE_ID=
CJ_PUBLISHER_ID=
CJ_LINK_SEARCH_URL=https://link-search.api.cj.com/v2/link-search
CJ_COMMISSION_API_URL=https://commissions.api.cj.com/query

IMPACT_ACCOUNT_SID=
IMPACT_AUTH_TOKEN=
IMPACT_API_BASE_URL=https://api.impact.com

YOUTUBE_API_KEY=
AFFILIATE_DB_PATH=data/affiliate.db
VITE_API_BASE_URL=http://localhost:8000
```

Do not commit `.env`.

## Validation

```bash
cd backend
ruff check .
pytest
```

V0.7 GitHub Actions validation passes backend Ruff, backend pytest, and the React production build.

## Next roadmap

1. Scheduled server-side CJ/Impact sync with retry/backoff and sync history.
2. Persist recommendation snapshots so performance changes can be compared over time.
3. Google Ads buyer-intent/search-demand data.
4. Search Console + GA4 ingestion.
5. Content assets tied to campaign/source/content IDs.
6. Controlled experiment tracking for A/B content and offer tests.
7. PostgreSQL deployment once SQLite volume is outgrown.
