# Affiliate AI Agent

AI-assisted affiliate opportunity research, forecasting, campaign planning, and performance learning.

## Current MVP (V0.4)

The agent now combines five evidence layers:

1. **Verified AI affiliate catalog** with official-program terms checked on a specific date, so the opportunity engine is useful even before private network credentials are configured.
2. **CJ live Link Search** for joined advertisers, commissions, tracking links, and network EPC.
3. **Impact live Partner API** for joined programs, tracking links, ads, and public payout/attribution terms.
4. **Direct affiliate page scanner** for user-supplied public program pages, extracting commission %, recurring language, cookie/attribution window, network hints, and application links.
5. **YouTube market research** for a lightweight interest/competition signal based on public video search and view statistics.

`POST /api/v1/opportunities/top` deduplicates those sources, calculates a commercial-readiness score, optionally adds a small YouTube market adjustment, and returns a final opportunity score with explicit evidence and confidence.

The scores are **prioritization heuristics, not profit forecasts**. Real earnings require approved affiliate relationships, valid tracking links, qualified traffic, conversions, and compliance with each program's terms.

## Safety and data rules

- API tokens stay in environment variables and are never committed.
- The direct scanner fetches only user-supplied public HTTP(S) pages, blocks obvious local/private targets, limits redirects, and caps page size.
- Missing commission, EPC, cookie, or market fields are not invented.
- Historical EPC is evidence, not a guarantee of future earnings.
- The system does not automate advertiser approval, impersonation, spam, or policy circumvention.
- Publishing and affiliate-program participation must follow each network, brand, and platform's rules.

## Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000 --env-file ../.env
```

API docs: `http://localhost:8000/docs`

Run validation:

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

Default Vite URL: `http://localhost:5173`.
Set `VITE_API_BASE_URL` if the backend is not running at `http://localhost:8000`.

## Credentials

Copy `.env.example` to `.env` and fill only the services you use:

```text
CJ_API_TOKEN=
CJ_WEBSITE_ID=
IMPACT_ACCOUNT_SID=
IMPACT_AUTH_TOKEN=
YOUTUBE_API_KEY=
VITE_API_BASE_URL=http://localhost:8000
```

Do not commit `.env`.

The verified catalog works without these credentials. CJ, Impact, and YouTube become live enrichment sources when configured.

## API endpoints

### Research

- `GET /api/v1/connectors/cj/status`
- `GET /api/v1/cj/links?keywords=vps&advertiser_ids=joined`
- `GET /api/v1/connectors/impact/status`
- `GET /api/v1/impact/programs`
- `GET /api/v1/impact/programs/{campaign_id}/public-terms`
- `GET /api/v1/impact/ads?campaign_id=...&ad_type=TEXT_LINK`
- `GET /api/v1/connectors/youtube/status`
- `GET /api/v1/youtube/market?query=AI%20voice`
- `POST /api/v1/direct/scan`
- `POST /api/v1/opportunities/top`

Example top-opportunity request:

```json
{
  "keywords": "AI software",
  "direct_urls": [],
  "include_cj": true,
  "include_impact": true,
  "include_verified_catalog": true,
  "enrich_impact_terms": true,
  "include_youtube": true,
  "youtube_probe_count": 3,
  "limit": 10
}
```

Without network credentials, a query such as `AI voice`, `vibe coding`, `AI agents`, or `AI visibility` can still return matching verified programs. Configure network/API credentials to add live account-specific data.

### Decision engine

- `POST /api/v1/score`
- `POST /api/v1/forecast`
- `POST /api/v1/campaign`

## Ranking model

### Commercial readiness

The base score uses evidence available for the offer:

- commission percentage;
- fixed payout when available;
- CJ historical EPC when available;
- cookie/attribution window;
- recurring commission terms;
- live tracking/application-link readiness;
- source quality and completeness.

### Market adjustment

If YouTube is configured, the engine samples public videos for a small number of top candidates and calculates:

- interest signal from median views and recent activity;
- competition signal from high-view and established videos.

Only a modest adjustment is applied so social popularity cannot overpower actual monetization evidence.

## Verified seed catalog

V0.4 includes a small reviewed seed catalog for current AI-related programs such as Semrush, Lovable, Hostinger Horizons, ElevenLabs, and Sintra AI. Each record carries a verification date and caveats. These records should be refreshed when program terms change; never assume a stored commission remains valid forever.

## Next roadmap

1. Google Ads keyword-demand and buyer-intent connector.
2. Google Trends integration when API access is available, with a fallback research workflow until then.
3. Persistent SQLite/Postgres storage for offers, tracking links, clicks, conversions, and commissions.
4. Campaign workspace that turns a selected opportunity into review/comparison/tutorial briefs.
5. Real EPC and conversion learning based on the user's own results.
6. Search Console/GA4 ingestion to connect content impressions → clicks → affiliate conversions → revenue.
