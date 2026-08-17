# Affiliate Intelligence Engine

V1 foundation for discovering, verifying, scoring, and tracking affiliate opportunities.

## What exists now

- SQLite schema for programs, scores, campaigns, content assets, links, clicks, conversions, commissions, and daily metrics.
- Explicit verification state so discovered claims cannot silently become trusted program terms.
- Deterministic opportunity scoring based on economics, attribution window, niche fit, conversion confidence, competition, approval friction, and verification quality.
- JSON candidate ingestion and ranking CLI.
- Unit tests for verification penalties, rejection handling, and candidate deduplication.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

On macOS/Linux use `source .venv/bin/activate`.

## Initialize the database

```bash
affiliate-intel --db data/affiliate_intel.db init-db
```

## Candidate format

```json
[
  {
    "slug": "example-tool",
    "name": "Example Tool",
    "product_url": "https://example.com",
    "affiliate_url": "https://example.com/affiliates",
    "commission_type": "recurring",
    "commission_rate_pct": 30,
    "lifetime_recurring": true,
    "cookie_days": 90,
    "monthly_price_from": 100,
    "niche_fit": 0.9,
    "conversion_confidence": 0.7,
    "competition_penalty": 0.4,
    "approval_friction": 0.2,
    "verification_status": "unverified",
    "source_url": "https://example.com/affiliates"
  }
]
```

## Rank candidates

```bash
affiliate-intel score-file candidates.json
```

## Ingest candidates

```bash
affiliate-intel --db data/affiliate_intel.db ingest candidates.json
```

## Scoring philosophy

The score is intentionally conservative. Unverified, stale, or rejected program terms receive strong penalties. This prevents the automation layer from allocating content production based on outdated affiliate pages or copied third-party claims.

## Next V1 slice

1. Authoritative-source verifier for affiliate terms.
2. Persist score snapshots and score history.
3. HTTP redirect/click tracker with campaign attribution.
4. Import conversions/commissions from affiliate networks.
5. Optimizer that reallocates content effort based on EPC, conversion rate, and revenue per 1,000 impressions.
