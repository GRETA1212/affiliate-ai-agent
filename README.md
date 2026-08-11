# Affiliate AI Agent

AI-assisted affiliate opportunity research, forecasting, campaign planning, and performance learning.

## Current MVP (V0.3)

The agent now supports three evidence sources:

1. **CJ live Link Search** for joined advertisers, commissions, tracking links, and network EPC;
2. **Impact live Partner API** for joined programs and available ads/tracking links;
3. **Direct affiliate page scanner** for public program pages supplied by URL, extracting commission %, recurring-language, cookie/attribution window, network hints, and application links.

The `/api/v1/opportunities/top` endpoint combines those sources and ranks them by **commercial readiness**. This score is deliberately not presented as a profit prediction: market demand, trend, competition, real CTR, conversion rate, and actual EPC still need to be measured or connected.

## Safety and data rules

- API tokens stay in environment variables and are never committed.
- The direct scanner fetches only user-supplied public HTTP(S) pages, blocks obvious local/private targets, limits redirects, and caps page size.
- The system does not automate advertiser approval, impersonation, spam, or policy circumvention.
- Publishing and affiliate-program participation must follow each network/brand/platform's terms.
- Historical EPC is evidence, not a guarantee of future earnings.

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

Run tests:

```bash
cd backend
pytest
ruff check .
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Default Vite URL: `http://localhost:5173`

Set `VITE_API_BASE_URL` if the backend is not running at `http://localhost:8000`.

## Credentials

Copy `.env.example` to `.env` and fill only the services you use:

```text
CJ_API_TOKEN=
CJ_WEBSITE_ID=
IMPACT_ACCOUNT_SID=
IMPACT_AUTH_TOKEN=
```

Do not commit `.env`.

## API endpoints

### Research

- `GET /api/v1/connectors/cj/status`
- `GET /api/v1/cj/links?keywords=vps&advertiser_ids=joined`
- `GET /api/v1/connectors/impact/status`
- `GET /api/v1/impact/programs`
- `GET /api/v1/impact/ads?campaign_id=...&ad_type=TEXT_LINK`
- `POST /api/v1/direct/scan`
- `POST /api/v1/opportunities/top`

Example top-opportunity request:

```json
{
  "keywords": "AI software",
  "direct_urls": [
    "https://example.com/affiliate-program"
  ],
  "include_cj": true,
  "include_impact": true,
  "limit": 10
}
```

### Decision engine

- `POST /api/v1/score`
- `POST /api/v1/forecast`
- `POST /api/v1/campaign`

## Current ranking model

The automatic top-opportunity list currently ranks **commercial readiness** using the evidence actually available from the source:

- commission percentage when present;
- CJ network EPC when present;
- cookie/attribution window when present;
- recurring commission language;
- tracking/application-link readiness;
- source quality and data completeness.

Missing fields are not invented. The next ranking upgrade is to add search demand, trend, competition, and then the user's real click/conversion/revenue data.

## Next roadmap

1. Google Ads keyword-demand connector.
2. Google Trends connector when API access is available, with a manual/public fallback until then.
3. YouTube competition research.
4. SQLite/Postgres storage for offers, links, clicks, conversions, and commissions.
5. Real EPC learning loop based on the user's own results.
6. Content-campaign generator tied to the top ranked opportunity.
