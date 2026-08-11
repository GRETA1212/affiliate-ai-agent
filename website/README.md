# Public affiliate website

This is the public, SEO-oriented content site for Affiliate AI Agent V0.8.

It is intentionally separate from:

- `frontend/` — the private research/campaign dashboard;
- `backend/` — tracking, network sync, revenue, EPC and performance advisor;
- `website/` — the public editorial site that can receive search/social traffic.

## Current pages

The build generates:

- `/`
- `/best-ai-tools/`
- `/ai-app-builders/`
- `/ai-voice/`
- `/ai-marketing/`
- `/comparisons/`
- `/tutorials/`
- `/about/`
- `/contact/`
- `/affiliate-disclosure/`
- `/privacy/`
- `/terms/`
- `/sitemap.xml`
- `/robots.txt`

The starter content does not fabricate hands-on testing, testimonials, earnings or affiliate approval.
Named product rankings should only be added after checking current product facts and commercial terms.

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

`SITE_URL` is used for canonical tags, sitemap URLs and structured data. The default is deliberately
`https://example.invalid` so a production build is visibly incomplete until a real domain is chosen.

## Affiliate links

Do not put fake or generic affiliate links into the editorial source.

After an affiliate program approves the publisher:

1. create the campaign in the private dashboard;
2. save the approved CJ/Impact/direct tracking link;
3. expose the backend on a public HTTPS tracking subdomain, for example `https://go.example.com`;
4. use the campaign redirect URL such as `https://go.example.com/elevenlabs-review` in the relevant public article;
5. add a clear affiliate disclosure near commercial links.

This keeps public content separate from private credentials and revenue analytics.

## Deployment

The site is static and can be deployed to any host that serves `website/dist/`, including static hosting
providers and object/CDN hosting. Configure the project build command as `npm run build` with the root
folder set to `website` and the publish/output directory set to `dist`.

Before commercial launch, replace the placeholder contact details and review the privacy policy and terms
for the final operating entity, analytics stack, target jurisdictions and hosting provider.
