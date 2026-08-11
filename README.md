# Affiliate AI Agent

AI-assisted affiliate opportunity research, forecasting, campaign planning, and performance learning.

## MVP goals

The first version focuses on the decision engine before live affiliate-network automation:

1. score affiliate opportunities from normalized market signals;
2. forecast clicks, conversions, revenue, and EPC;
3. generate a useful, non-spam campaign plan;
4. expose the engine through a FastAPI API;
5. provide a small React dashboard;
6. run backend tests in GitHub Actions.

Future connectors are planned for CJ, Impact, Google Ads/Trends, YouTube, Search Console, GA4, and link tracking. Credentials are never committed.

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

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Default Vite URL: `http://localhost:5173`

Set `VITE_API_BASE_URL` if the backend is not running at `http://localhost:8000`.

## Core scoring model

The MVP opportunity score combines demand, buyer intent, trend, commission attractiveness, network EPC signal, and inverse competition. Every signal is normalized to 0-100. The weights are deliberately explicit and deterministic so they can later be learned from real conversion data.

This repository does not automate advertiser approval, impersonation, spam, or policy circumvention. Publishing and affiliate-program participation must follow the relevant network and platform terms.
