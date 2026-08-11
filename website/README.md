# Public affiliate website

This is the public, SEO-oriented editorial site for Affiliate AI Agent **V0.9**.

It is intentionally separate from:

- `frontend/` — the private research/campaign dashboard;
- `backend/` — tracking, network sync, revenue, EPC and performance advisor;
- `website/` — the public editorial site that can receive search/social traffic.

## Current public content

The build includes the original category/legal foundation plus five named, fact-checked commercial buyer guides:

- `/comparisons/lovable-vs-hostinger-horizons/`
- `/ai-app-builders/lovable-buyer-guide/`
- `/ai-voice/elevenlabs-buyer-guide/`
- `/ai-marketing/semrush-ai-visibility-buyer-guide/`
- `/best-ai-tools/small-business-2026/`

The category indexes for Best AI Tools, App Builders, AI Voice, AI Marketing and Comparisons now link directly to these guides.

Every named guide:

- shows a visible fact-check date;
- links to official vendor sources;
- separates verified facts from editorial judgment;
- avoids invented hands-on testing, testimonials and earnings claims;
- explains that affiliate economics are not evidence of product quality;
- uses direct official product links until a real affiliate relationship/link exists.

See `FACT_CHECK.md` for the source register and claims that must be re-verified during future refreshes.

## Build

No third-party runtime package is required.

```bash
cd website
npm run build
```

Output:

```text
website/dist/
```

## Local preview

```bash
cd website
npm run dev
```

Default preview:

```text
http://127.0.0.1:4174
```

## Production environment

Set these when building for the real domain:

```text
SITE_NAME=Your final brand name
SITE_URL=https://www.yourdomain.com
CONTACT_EMAIL=hello@yourdomain.com
```

`SITE_URL` is used for canonical tags, sitemap URLs and structured data. The default is deliberately `https://example.invalid` so a production build is visibly incomplete until a real domain is chosen.

## Affiliate links

Do not put fake or generic affiliate links into the editorial source.

After an affiliate program approves the publisher:

1. create the campaign in the private dashboard;
2. save the approved CJ/Impact/direct tracking link;
3. expose the backend on a public HTTPS tracking subdomain, for example `https://go.example.com`;
4. use the campaign redirect URL such as `https://go.example.com/elevenlabs-review` in the relevant public article;
5. add a clear affiliate disclosure near commercial links;
6. mark affiliate links as sponsored when they are added.

This keeps public content separate from private credentials and revenue analytics.

## Fact checking

Named product and pricing claims are maintained in `FACT_CHECK.md`.

Current fact-check date: **11 August 2026**.

Before launch or a major content refresh, re-check:

- prices and renewal terms;
- plan limits and features;
- affiliate commissions/cookie windows;
- prohibited promotional methods;
- product ownership/export statements;
- public claims about data scale or supported platforms.

## Deployment

The site is static and can be deployed to any host that serves `website/dist/`, including static hosting providers and object/CDN hosting. Configure the project build command as `npm run build` with the root folder set to `website` and the publish/output directory set to `dist`.

Before commercial launch, replace the placeholder contact details and review the privacy policy and terms for the final operating entity, analytics stack, target jurisdictions and hosting provider.
