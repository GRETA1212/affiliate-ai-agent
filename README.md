# Affiliate AI Agent

AI-assisted affiliate opportunity research, campaign tracking, revenue measurement, forecasting, and performance learning.

## Current MVP (V0.5)

The agent now covers the first complete measurable affiliate loop:

1. **Find opportunities** from a verified AI-affiliate catalog, CJ, Impact, direct affiliate pages, and YouTube market signals.
2. **Create a persistent campaign** with your own approved affiliate tracking URL.
3. **Publish the generated `/go/{slug}` tracking link** instead of the raw network URL.
4. **Record human/bot-aware clicks** before redirecting to the affiliate network.
5. **Record network conversions and commissions** in SQLite.
6. **Calculate your real conversion rate and EPC by currency** from approved commissions.
7. **Pause/reactivate campaigns** without deleting history.

The opportunity score remains a prioritization heuristic, not a profit guarantee. Real earnings still require approved affiliate accounts, valid tracking links, qualified traffic, conversions, and compliance with program/platform rules.

## Persistent campaign database

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
- `conversions` — network/external ID, sale amount, commission amount, currency, status.

Raw IP addresses are deliberately not stored. Obvious crawler/bot user-agents are recorded but excluded from human-click, conversion-rate, and EPC calculations.

Revenue is never summed across currencies. Metrics return maps such as:

```json
{
  "approved_revenue_by_currency": {"EUR": 125.0, "USD": 40.0},
  "epc_by_currency": {"EUR": 0.625, "USD": 0.2}
}
```

## Tracked links

An active campaign with slug `elevenlabs-review` gets a local tracking route:

```text
http://localhost:8000/go/elevenlabs-review
```

Optional campaign attribution can be added:

```text
/go/elevenlabs-review?source=youtube&medium=video&content=review-1
```

The backend records the click and immediately redirects to the stored affiliate tracking URL.

For real public traffic, deploy the backend to a public HTTPS domain and use that domain for `/go/...` links. `localhost` is only suitable for testing on your own machine.

## Campaign workspace

The React dashboard now includes a persistent workspace where you can:

- start a campaign from a ranked opportunity;
- paste your approved CJ/Impact/direct affiliate tracking URL;
- create draft/active/paused campaigns;
- see human clicks and excluded bot clicks;
- log approved, pending, or reversed conversions;
- store network order/action IDs to prevent duplicate imports;
- see approved revenue, pending revenue, conversion rate, and real EPC;
- activate/pause a tracked redirect without losing historical data.

A public affiliate signup/program page is **not** a substitute for your personal tracking URL and will not create commission attribution.

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

## Environment

Copy `.env.example` to `.env` and fill only the services you use:

```text
CJ_API_TOKEN=
CJ_WEBSITE_ID=
IMPACT_ACCOUNT_SID=
IMPACT_AUTH_TOKEN=
YOUTUBE_API_KEY=
AFFILIATE_DB_PATH=data/affiliate.db
VITE_API_BASE_URL=http://localhost:8000
```

Never commit `.env`, network tokens, or personal affiliate links that contain credentials/secrets.

## Main API endpoints

### Opportunity research

- `GET /api/v1/connectors/cj/status`
- `GET /api/v1/cj/links`
- `GET /api/v1/connectors/impact/status`
- `GET /api/v1/impact/programs`
- `GET /api/v1/impact/programs/{campaign_id}/public-terms`
- `GET /api/v1/impact/ads`
- `GET /api/v1/connectors/youtube/status`
- `GET /api/v1/youtube/market`
- `POST /api/v1/direct/scan`
- `POST /api/v1/opportunities/top`

### Campaign workspace

- `GET /api/v1/workspace/summary`
- `POST /api/v1/workspace/campaigns`
- `GET /api/v1/workspace/campaigns`
- `GET /api/v1/workspace/campaigns/{campaign_id}`
- `PATCH /api/v1/workspace/campaigns/{campaign_id}`
- `GET /api/v1/workspace/campaigns/{campaign_id}/metrics`
- `POST /api/v1/workspace/campaigns/{campaign_id}/conversions`
- `GET /api/v1/workspace/campaigns/{campaign_id}/conversions`
- `PATCH /api/v1/workspace/conversions/{conversion_id}`
- `GET /go/{slug}`

Example campaign:

```json
{
  "name": "ElevenLabs YouTube review",
  "product_name": "ElevenLabs",
  "affiliate_url": "https://your-approved-network-tracking-link.example",
  "status": "active",
  "source": "verified",
  "opportunity_score": 87.4
}
```

Example approved conversion:

```json
{
  "commission_amount": 22.0,
  "sale_amount": 100.0,
  "currency": "USD",
  "status": "approved",
  "network": "impact",
  "external_id": "network-action-123"
}
```

## Safety and data rules

- API tokens remain environment-only.
- Missing commercial/market fields are not invented.
- Historical network EPC is evidence, not guaranteed future EPC.
- The direct scanner only fetches user-supplied public HTTP(S) pages and blocks obvious private/local targets.
- Click tracking does not store raw IP addresses.
- Duplicate network/external conversion IDs are rejected.
- Pending and reversed commissions do not count as approved revenue.
- Revenue/EPC is kept separate by currency.
- The system does not automate fake clicks, fake conversions, advertiser approval bypass, spam, cookie stuffing, or deceptive cloaking.

## Next roadmap

1. Automatic CJ/Impact commission synchronization into the conversion table.
2. Google Ads keyword demand and buyer-intent connector.
3. Search Console/GA4 ingestion to connect impressions → visits → affiliate clicks → conversions.
4. Content asset records for article/video/short IDs tied to each campaign.
5. Daily/weekly performance snapshots and winner/loser detection.
6. PostgreSQL/Postgres migration path for a deployed multi-user version.
