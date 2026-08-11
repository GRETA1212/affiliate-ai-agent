# Affiliate AI Agent

AI-assisted affiliate opportunity research, public editorial content, campaign tracking, CJ/Impact commission sync, real revenue measurement, and evidence-based campaign recommendations.

## Current system — V0.9

V0.9 turns the V0.8 public-site foundation into a fact-checked commercial-content layer while keeping the V0.7 tracking/revenue engine intact.

```text
Search / social / direct traffic
            ↓
      website/ public site
            ↓
 fact-checked buyer guide/comparison
            ↓
  public /go/{campaign} redirect
            ↓
       affiliate network
            ↓
       sale / commission
            ↓
       backend + SQLite
            ↓
      real CVR + real EPC
            ↓
      Performance Advisor
            ↓
 scale / test / optimize / pause
```

The repository has three distinct applications:

- `website/` — public, SEO-oriented editorial site;
- `frontend/` — private research, campaign and performance dashboard;
- `backend/` — opportunity research, tracking redirects, CJ/Impact sync, SQLite revenue and performance advisor.

## Public website — V0.9

The static site now includes five named, fact-checked commercial guides in addition to the category/legal foundation:

- `/comparisons/lovable-vs-hostinger-horizons/`
- `/ai-app-builders/lovable-buyer-guide/`
- `/ai-voice/elevenlabs-buyer-guide/`
- `/ai-marketing/semrush-ai-visibility-buyer-guide/`
- `/best-ai-tools/small-business-2026/`

The Best AI Tools, App Builders, AI Voice, AI Marketing and Comparisons indexes now surface these guides directly.

Commercial-content safeguards:

- visible **11 August 2026** fact-check date;
- official vendor sources linked on every named guide;
- source/claim register in `website/FACT_CHECK.md`;
- no invented hands-on testing, testimonials, affiliate approval or earnings;
- pricing language distinguishes current/promotional page values from permanent guarantees;
- affiliate economics are explicitly separated from product-quality judgments;
- direct official product links are used until an approved affiliate link exists.

Build the public site:

```bash
cd website
npm run build
```

Preview locally:

```bash
cd website
npm run dev
```

Open:

```text
http://127.0.0.1:4174
```

Before a real deployment set:

```text
SITE_NAME=Your final brand
SITE_URL=https://www.yourdomain.com
CONTACT_EMAIL=hello@yourdomain.com
```

See `website/README.md` for deployment and affiliate-link workflow details.

## Measurable affiliate loop

1. Find opportunities from the verified AI-affiliate catalog, CJ, Impact, direct affiliate pages and YouTube signals.
2. Create a persistent campaign with an approved affiliate tracking URL.
3. Bind the campaign to CJ or Impact when applicable.
4. Publish `/go/{slug}` on a public HTTPS tracking host.
5. Record human/bot-aware clicks before redirecting.
6. Sync CJ commissions and Impact actions into SQLite.
7. Reconcile approvals, reversals and CJ correction deltas without double-counting.
8. Calculate real conversion rate and EPC by currency.
9. Classify campaigns as winner, loser, promising, neutral, insufficient-data or inactive.
10. Recommend scale, increase-test, hold, optimize, pause/rework or collect-data.

Opportunity scores and advisor outputs are decision aids, not profit guarantees. Real earnings require approved affiliate accounts, qualified traffic, conversions and compliance with network/platform rules.

## Performance Advisor

```text
GET /api/v1/performance/recommendations
```

Default decision thresholds:

- 50 human clicks minimum sample;
- 150 clicks for a strong no-conversion review;
- 2% healthy-test CVR;
- 0.5% low-CVR warning;
- 1.25× same-currency peer median EPC for a relative winner;
- 0.5× same-currency peer median EPC for a relative weak signal after enough traffic.

Campaigns are never compared across currencies.

## Persistent database and tracking

Default database:

```text
data/affiliate.db
```

SQLite stores campaigns, clicks, canonical conversions, CJ/Impact bindings, normalized raw network events and sync state. Raw IP addresses are deliberately not stored. Bot clicks are excluded from human KPIs. Pending and reversed commissions do not count as approved revenue.

Local tracked-link example:

```text
http://localhost:8000/go/example-campaign
```

For actual external traffic, deploy the backend on a public HTTPS tracking domain such as:

```text
https://go.yourdomain.com/example-campaign
```

## Run the private system locally

Backend:

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000 --env-file ../.env
```

Dashboard:

```bash
cd frontend
npm install
npm run dev
```

Open the dashboard at `http://localhost:5173` and API docs at `http://localhost:8000/docs`.

## Private credentials

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

Do not commit `.env` or paste account secrets into public issues, articles or source files.

## Validation

GitHub Actions validates all three layers:

- backend Ruff;
- backend pytest;
- private React dashboard production build;
- public website static build;
- homepage, sitemap and affiliate-disclosure page;
- all five named commercial guides;
- fact-check date rendered into the comparison output.

## Next roadmap

1. Choose a final brand/domain and deploy `website/dist/` publicly.
2. Deploy the backend on a public HTTPS tracking subdomain.
3. Add 5–10 more evidence-based articles around the strongest buyer-intent clusters.
4. Apply to appropriate affiliate programs using the live editorial property.
5. Replace direct product CTAs with approved `/go/{slug}` campaign links and `rel="sponsored"` disclosure.
6. Add automated fact-refresh checks for prices/program terms that flag stale articles before publication.
7. Add scheduled server-side CJ/Impact sync with retry/backoff and sync history.
8. Add Search Console + GA4 or privacy-conscious traffic analytics.
9. Persist recommendation snapshots to show performance changes over time.
10. Add controlled content/offer experiments.
