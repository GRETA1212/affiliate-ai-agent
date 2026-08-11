# Affiliate AI Agent

AI-assisted affiliate opportunity research, campaign tracking, automatic commission sync,
revenue measurement, forecasting, and performance learning.

## Current MVP (V0.6)

The agent now covers a measurable affiliate loop:

1. **Find opportunities** from the verified AI-affiliate catalog, CJ, Impact, direct
   affiliate pages, and YouTube market signals.
2. **Create a persistent campaign** with your approved affiliate tracking URL.
3. **Bind the campaign to CJ or Impact** using the network advertiser/program ID.
4. **Publish the `/go/{slug}` tracking link** instead of the raw network URL.
5. **Record human/bot-aware clicks** before redirecting to the affiliate network.
6. **Sync CJ commissions and Impact actions** into SQLite.
7. **Reconcile approvals, reversals, and CJ correction deltas** without double-counting.
8. **Calculate real conversion rate and EPC by currency** from approved commissions.
9. **Keep unmatched network events** for manual assignment instead of guessing attribution.

Opportunity scores are prioritization heuristics, not profit forecasts. Real earnings require
approved affiliate accounts, valid tracking links, qualified traffic, conversions, and compliance
with program/platform rules.

## Persistent database

By default the backend creates:

```text
data/affiliate.db
```

Set another location with:

```text
AFFILIATE_DB_PATH=data/affiliate.db
```

SQLite tables:

- `campaigns` — offer, source, opportunity score, affiliate URL, slug, lifecycle status;
- `clicks` — timestamp, campaign, source/medium/content, referrer, user-agent, bot flag;
- `conversions` — canonical campaign conversions used for revenue/EPC;
- `campaign_bindings` — network, program/advertiser ID, campaign attribution token;
- `network_events` — raw normalized CJ commission records and Impact actions;
- `sync_state` — last successful sync, cursor, and error state by network.

Raw IP addresses are deliberately not stored. Obvious crawler/bot user-agents are recorded but
excluded from human-click, conversion-rate, and EPC calculations.

Revenue is never summed across currencies. Metrics return maps such as:

```json
{
  "approved_revenue_by_currency": {"EUR": 125.0, "USD": 40.0},
  "epc_by_currency": {"EUR": 0.625, "USD": 0.2}
}
```

## Automatic CJ + Impact synchronization

### Impact

Impact actions are matched in this order:

1. `SubId1` → campaign attribution token;
2. if there is no token match, a **single unambiguous** campaign binding for the Impact
   `ProgramId`.

The app can create an Impact tracking link that uses the campaign slug as `subId1`. This makes
multiple campaigns for the same program independently attributable.

Action states are normalized as:

- `PENDING` → pending;
- `APPROVED` → approved;
- `REVERSED` → reversed.

Re-running sync updates the same conversion rather than creating a duplicate.

### CJ

CJ Commission Detail records are stored as signed delta events. Corrections are grouped using
`originalActionId`, then `orderId`, then `commissionId` as a fallback. The group is recalculated
every time new commission records arrive.

This matters because a CJ cancellation/correction can arrive as another commission record with a
negative commission amount. V0.6 keeps both raw events and materializes one canonical campaign
conversion from their net result.

CJ matching uses:

1. `shopperId` when it matches a campaign attribution token;
2. otherwise one unambiguous campaign binding for the CJ `AdvertiserId`.

The app does **not** invent or rewrite CJ SID parameters. If more than one campaign could match the
same advertiser and no unique attribution token is present, the event remains unmatched.

## Unmatched events

Automatic sync never guesses when attribution is ambiguous.

Use:

```text
GET /api/v1/workspace/unmatched
```

Then assign an event:

```text
POST /api/v1/workspace/network-events/{event_id}/assign/{campaign_id}
```

For CJ, assigning one correction event assigns its complete correction group before recalculating
the canonical conversion.

## Tracked links

An active campaign with slug `elevenlabs-review` gets:

```text
http://localhost:8000/go/elevenlabs-review
```

Optional traffic attribution:

```text
/go/elevenlabs-review?source=youtube&medium=video&content=review-1
```

For real public traffic, deploy the backend to a public HTTPS domain. `localhost` is only for local
testing.

## Campaign workspace

The React dashboard supports:

- starting a campaign from a ranked opportunity;
- storing an approved affiliate tracking URL;
- binding the campaign to CJ or Impact;
- generating a tagged Impact tracking link when Impact credentials are configured;
- syncing the last seven days from CJ + Impact;
- seeing fetched, matched, unmatched, and updated-conversion counts;
- manual conversion entry as a fallback;
- activating/pausing tracked redirects without deleting history;
- approved revenue, pending revenue, conversion rate, and real EPC.

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
cd backend
ruff check .
pytest
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Default URL:

```text
http://localhost:5173
```

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

CJ Link Search needs `CJ_API_TOKEN` + `CJ_WEBSITE_ID`.
CJ revenue sync needs `CJ_API_TOKEN` + `CJ_PUBLISHER_ID`.
Impact research, tracking-link creation, and action sync need the Impact credentials.

## V0.6 workspace API

### Campaigns and tracking

- `GET /api/v1/workspace/summary`
- `POST /api/v1/workspace/campaigns`
- `GET /api/v1/workspace/campaigns`
- `PATCH /api/v1/workspace/campaigns/{campaign_id}`
- `GET /api/v1/workspace/campaigns/{campaign_id}/metrics`
- `POST /api/v1/workspace/campaigns/{campaign_id}/conversions`
- `GET /go/{slug}`

### Network reconciliation

- `PUT /api/v1/workspace/campaigns/{campaign_id}/binding`
- `GET /api/v1/workspace/campaigns/{campaign_id}/binding`
- `POST /api/v1/workspace/campaigns/{campaign_id}/impact-tracking-link`
- `POST /api/v1/workspace/sync`
- `GET /api/v1/workspace/sync/status`
- `GET /api/v1/workspace/unmatched`
- `POST /api/v1/workspace/network-events/{event_id}/assign/{campaign_id}`

Example sync:

```json
{
  "networks": ["cj", "impact"],
  "lookback_days": 7
}
```

A connector that is not configured returns a warning inside its sync result; it does not prevent
the other configured network from syncing.

## Research API

- `GET /api/v1/connectors/cj/status`
- `GET /api/v1/connectors/cj/commissions/status`
- `GET /api/v1/cj/links`
- `GET /api/v1/connectors/impact/status`
- `GET /api/v1/impact/programs`
- `GET /api/v1/impact/programs/{campaign_id}/public-terms`
- `GET /api/v1/impact/ads`
- `GET /api/v1/connectors/youtube/status`
- `GET /api/v1/youtube/market`
- `POST /api/v1/direct/scan`
- `POST /api/v1/opportunities/top`

## Safety and accounting rules

- Secrets stay in environment variables.
- Network event IDs are idempotent: repeated syncs update rather than duplicate.
- Pending and reversed commissions do not count as approved revenue.
- CJ correction records are netted by correction group.
- Ambiguous attribution remains unmatched rather than being silently assigned.
- Bot clicks are excluded from human KPIs.
- Currency totals are kept separate.
- A public affiliate signup/program page is not a personal affiliate tracking link.
- Automatic publishing, fake clicks/conversions, cookie stuffing, and approval bypass are not part
  of this project.

## Next roadmap

1. Scheduled server-side sync jobs with retry/backoff and sync history.
2. Google Ads buyer-intent/search-demand data.
3. Search Console + GA4 ingestion.
4. Persisted content assets and content-to-campaign attribution.
5. Relative winner/loser detection from real campaign performance.
6. PostgreSQL deployment path once local SQLite volume is outgrown.
