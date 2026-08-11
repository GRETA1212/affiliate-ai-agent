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

## Persistent database

Default database:

```text
data/affiliate.db
```

Override with:

```text
AFFILIATE_DB_PATH=data/affiliate.db
```

Tables include:

- `campaigns` — offer, affiliate URL, slug, source, opportunity score and lifecycle status;
- `clicks` — timestamp, source/medium/content, referrer, user-agent and bot flag;
- `conversions` — canonical approved/pending/reversed campaign conversions;
- `campaign_bindings` — CJ/Impact program IDs and campaign attribution token;
- `network_events` — normalized raw CJ commission records and Impact actions;
- `sync_state` — network sync state and errors.

Raw IP addresses are deliberately not stored. Bot clicks are excluded from human-click, conversion-rate, and EPC calculations.

Revenue and EPC are never merged across currencies.

## Winner / loser advisor

Endpoint:

```text
GET /api/v1/performance/recommendations
```

Default decision thresholds:

- minimum sample: **50 human clicks**;
- hard no-conversion review: **150 human clicks**;
- healthy test CVR: **2%**;
- low CVR warning: **0.5%**;
- relative winner: real EPC at least **1.25×** the same-currency peer median;
- relative weak signal: real EPC at or below **0.5×** the same-currency peer median after enough traffic.

The thresholds are query parameters, so they can be tuned without changing code.

The advisor returns:

- classification: `winner`, `loser`, `promising`, `neutral`, `insufficient_data`, or `inactive`;
- recommended action: `scale`, `increase_test`, `hold`, `optimize`, `pause_or_rework`, `collect_data`, or `none`;
- confidence and priority;
- real clicks, approved/pending conversions, CVR, revenue and EPC;
- same-currency peer EPC baseline;
- reasons and concrete next actions;
- EPC leader for each currency.

Important: campaigns are **never compared across currencies**. A USD EPC is not treated as directly comparable to a EUR EPC.

## Automatic CJ + Impact synchronization

### Impact

Impact actions are matched by:

1. exact `SubId1` campaign attribution token;
2. otherwise a single unambiguous bound Impact `ProgramId`.

The app can generate a tagged Impact tracking link using the campaign slug as `subId1`. Re-running sync updates the same normalized event/conversion instead of duplicating it.

### CJ

CJ Commission Detail records are preserved as signed events. Corrections are grouped and netted before one canonical campaign conversion is materialized. Matching prefers `shopperId` when it matches a campaign token, then one unambiguous CJ `AdvertiserId` binding.

Ambiguous events remain unmatched instead of being guessed.

## Unmatched events

```text
GET /api/v1/workspace/unmatched
POST /api/v1/workspace/network-events/{event_id}/assign/{campaign_id}
```

## Tracked links

Example local test link:

```text
http://localhost:8000/go/elevenlabs-review
```

Traffic attribution:

```text
/go/elevenlabs-review?source=youtube&medium=video&content=review-1
```

For real external traffic, deploy the backend on a public HTTPS domain. `localhost` is only for local testing.

## Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000 --env-file ../.env
```

API docs:

```text
http://localhost:8000/docs
```

Validation:

```bash
ruff check .
pytest
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The React UI contains opportunity research, the persistent campaign workspace, CJ/Impact sync controls, real revenue/EPC metrics, and the V0.7 performance advisor.

## Credentials

Copy `.env.example` to `.env` and fill only the services you use:

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

## Main APIs

Research:

```text
POST /api/v1/opportunities/top
GET  /api/v1/cj/links
GET  /api/v1/impact/programs
GET  /api/v1/youtube/market
```

Campaign/revenue:

```text
POST /api/v1/workspace/campaigns
GET  /api/v1/workspace/campaigns
GET  /api/v1/workspace/summary
PUT  /api/v1/workspace/campaigns/{campaign_id}/binding
POST /api/v1/workspace/campaigns/{campaign_id}/impact-tracking-link
POST /api/v1/workspace/sync
GET  /api/v1/workspace/unmatched
```

Performance:

```text
GET /api/v1/performance/recommendations
```

## Accounting and safety rules

- Secrets stay in environment variables.
- Repeated network syncs update instead of duplicate.
- Pending and reversed commissions do not count as approved revenue.
- CJ correction records are netted by correction group.
- Ambiguous attribution remains unmatched.
- Bot clicks are excluded from human KPIs.
- Currency totals and EPC comparisons remain separate.
- A public affiliate signup page is not a personal tracking link.
- Fake clicks/conversions, cookie stuffing, approval bypass, deceptive reviews, and uncontrolled auto-publishing are not part of the project.

## Next roadmap

1. Scheduled server-side CJ/Impact sync with retry/backoff and sync history.
2. Persist recommendation snapshots so the agent can show how a campaign changed over time.
3. Google Ads buyer-intent/search-demand data.
4. Search Console + GA4 ingestion.
5. Content assets tied to campaign/source/content IDs.
6. Controlled experiment tracking (A/B content angles and offers).
7. PostgreSQL deployment path once SQLite volume is outgrown.
