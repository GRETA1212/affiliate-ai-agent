# Affiliate AI Agent

AI-assisted affiliate opportunity research, public editorial content, campaign tracking, CJ/Impact commission sync, real revenue measurement, and evidence-based campaign recommendations.

## Current system — V0.8

V0.8 adds the public traffic layer to the V0.7 research/tracking engine.

```text
Search / social / direct traffic
            ↓
      website/ public site
            ↓
    helpful guide / comparison
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

The repository now has three distinct applications:

- `website/` — public, SEO-oriented editorial site;
- `frontend/` — private research, campaign and performance dashboard;
- `backend/` — opportunity research, tracking redirects, CJ/Impact sync, SQLite revenue and performance advisor.

## Public website — V0.8

The new static public site is designed to be deployable before affiliate-account approval. It includes:

- homepage;
- Best AI Tools buyer guide;
- AI App Builders category guide;
- AI Voice category guide;
- AI Marketing category guide;
- comparisons hub;
- tutorials hub;
- About + editorial methodology;
- Contact;
- Affiliate Disclosure;
- Privacy Policy starter;
- Terms of Use starter;
- canonical metadata;
- Open Graph metadata;
- Schema.org structured data;
- `sitemap.xml`;
- `robots.txt`;
- responsive mobile layout.

The starter content deliberately avoids fake hands-on claims, fabricated reviews and fake earnings. Named rankings should only be added after current product facts and commercial terms are checked.

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

See `website/README.md` for the deployment and affiliate-link workflow.

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
- generated homepage, sitemap and affiliate-disclosure page.

## Next roadmap

1. Choose and connect the final domain.
2. Deploy `website/dist/` publicly.
3. Deploy the backend on a public HTTPS tracking subdomain.
4. Publish several evidence-based named product comparisons using current official facts.
5. Apply to affiliate networks/programs using the live editorial site.
6. Replace approved campaign links with `/go/{slug}` tracking URLs.
7. Add scheduled server-side CJ/Impact sync with retry/backoff and sync history.
8. Add Search Console + GA4 or privacy-conscious traffic analytics.
9. Persist recommendation snapshots to show performance changes over time.
10. Add controlled content/offer experiments.
