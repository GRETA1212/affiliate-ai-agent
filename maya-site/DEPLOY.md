# Maya.exe Vercel deployment safety runbook

This site must deploy only to the dedicated Maya.exe Vercel project.

## Locked production target

- Project name: `maya-exe`
- Project ID: `prj_SX8g02SukEU1Vs77nDSFDL3oYOmt`
- Team/org ID: `team_Px8b8Y3imWCFQMeeER7xXoOr`
- Production domain: `https://maya-exe.vercel.app`

Do **not** deploy this directory to `ai-tool-compass-greta` or any other Vercel project.

## Local preflight

From the repository root:

```bash
cd maya-site
npm install
MAYA_SITE_URL=https://maya-exe.vercel.app npm run build
```

Confirm these files exist in `dist/`:

```text
dist/index.html
dist/tiktok-shop/index.html
dist/shop-the-look/ai-picked-makeup/index.html
dist/sitemap.xml
```

The V001 page must contain the virtual-creator disclosure and must not contain an active product link until the exact listing is verified.

## Safe Vercel CLI targeting

Vercel CLI supports selecting a project directly by project ID. Use the explicit project ID on every deployment command rather than relying on whatever project is currently linked in another directory.

First create a preview:

```bash
vercel deploy --cwd maya-site --project prj_SX8g02SukEU1Vs77nDSFDL3oYOmt
```

Verify the preview homepage and these routes before production:

```text
/
/tiktok-shop/
/shop-the-look/ai-picked-makeup/
/affiliate-disclosure/
/sitemap.xml
```

Only after preview verification, deploy production explicitly to the same project:

```bash
vercel deploy --prod --cwd maya-site --project prj_SX8g02SukEU1Vs77nDSFDL3oYOmt
```

Then verify:

```text
https://maya-exe.vercel.app/
https://maya-exe.vercel.app/tiktok-shop/
https://maya-exe.vercel.app/shop-the-look/ai-picked-makeup/
https://maya-exe.vercel.app/affiliate-disclosure/
```

## Production checks

A deployment is not considered complete until:

1. production deployment status is READY
2. homepage returns 200
3. V001 Shop-the-Look route returns 200
4. TikTok Shop route returns 200
5. no unverified affiliate destination has become active
6. canonical URLs point to `https://maya-exe.vercel.app`
7. `robots.txt` and `sitemap.xml` reference the Maya domain
8. AI Tool Compass remains untouched

## Rollback rule

If the V001 route fails, canonical URLs point elsewhere, or another Vercel project appears in the deployment target, stop and do not promote the deployment. Keep the currently working Maya production deployment until the target mismatch is resolved.
