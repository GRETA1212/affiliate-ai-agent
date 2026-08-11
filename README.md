# Affiliate AI Agent

AI-assisted affiliate opportunity research, forecasting, campaign planning, and performance learning.

## MVP goals

The current MVP focuses on the decision engine plus the first live affiliate-network connector:

1. search live CJ affiliate links from a configured publisher account;
2. normalize CJ commission and EPC data without confusing EPC per 100 clicks with per-click earnings;
3. score affiliate opportunities from normalized market signals;
4. forecast clicks, conversions, revenue, and EPC;
5. generate a useful, non-spam campaign plan;
6. expose the engine through a FastAPI API;
7. provide a small React dashboard;
8. run backend and frontend checks in GitHub Actions.

Impact, Google Ads/Trends, YouTube, Search Console, GA4, and link tracking are planned next. Credentials are never committed.

## Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

Run tests:

```bash
cd backend
pytest
```

## Configure CJ

CJ's API uses a Personal Access Token. Do not put the token in frontend code or commit it to Git.

Create a root `.env` file from `.env.example` and set:

```text
CJ_API_TOKEN=your_personal_access_token
CJ_WEBSITE_ID=your_property_pid
```

Then start the backend from `backend/` with the root environment file:

```bash
uvicorn app.main:app --reload --port 8000 --env-file ../.env
```

Useful endpoints:

```text
GET /api/v1/connectors/cj/status
GET /api/v1/cj/links?keywords=vps&advertiser_ids=joined
```

CJ Link Search documentation currently describes 7-day and 3-month EPC at the link level. CJ EPC is earnings per 100 clicks, so the backend returns both `*_epc_per_100_clicks` and `*_epc_per_click` fields explicitly.

See `docs/CJ_CONNECTOR.md` for setup and official CJ documentation links.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Default Vite URL: `http://localhost:5173`

Set `VITE_API_BASE_URL` if the backend is not running at `http://localhost:8000`.

The dashboard contains a live CJ keyword search. If CJ credentials are missing, the backend returns a configuration message instead of exposing or requesting secrets in the browser.

## Core scoring model

The MVP opportunity score combines demand, buyer intent, trend, commission attractiveness, network EPC signal, and inverse competition. Every signal is normalized to 0-100. The weights are deliberately explicit and deterministic so they can later be learned from real conversion data.

This repository does not automate advertiser approval, impersonation, spam, or policy circumvention. Publishing and affiliate-program participation must follow the relevant network and platform terms.
