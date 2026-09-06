# CJ live connector

The CJ connector is the first live affiliate-network integration in the project.

## What it does

The connector calls CJ's publisher Link Search REST API and normalizes link-level data for the Affiliate AI Agent. It currently supports:

- joined or non-joined advertiser filters;
- keyword, category and link-type search;
- promotion type and target-country filters;
- deep-linking filters;
- pagination;
- sale, lead and click commission text;
- 7-day and 3-month EPC;
- CJ tracking URL and destination URL.

CJ reports link EPC as earnings per 100 clicks. The normalized response therefore exposes both the original per-100-click EPC and an explicit per-click equivalent so the forecasting engine does not accidentally treat the CJ value as earnings for one click.

## Authentication

CJ API calls use a Personal Access Token in the `Authorization: Bearer ...` header. Developer keys are deprecated for new APIs.

Required environment variables:

```text
CJ_API_TOKEN=your_personal_access_token
CJ_WEBSITE_ID=your_property_pid
```

Never place the token in frontend code or commit it to Git.

## Run locally

From `backend/`:

```bash
uvicorn app.main:app --reload --port 8000 --env-file ../.env
```

Then query:

```text
GET /api/v1/cj/links?keywords=vps&advertiser_ids=joined
```

The dashboard also exposes a CJ keyword-search box when the backend is configured.

## Official references

- Authentication: https://developers.cj.com/authentication/overview
- Personal access tokens: https://developers.cj.com/account/personal-access-tokens
- Link Search API: https://developers.cj.com/docs/rest-apis/link-search

The Link Search API currently documents a publisher limit of 25 calls per minute. The MVP performs user-triggered searches only; background crawling and rate-limit scheduling belong in a later connector orchestration layer.
