# Maya.exe

Standalone static site for the Maya.exe virtual beauty-tech creator brand.

## Build

```bash
cd maya-site
npm run build
```

Output is written to `maya-site/dist/`.

## Production environment

Set `MAYA_SITE_URL` to the final public origin before deployment.

TikTok Shop product buttons stay disabled until a verified product URL is supplied. Supported variables:

- `TIKTOK_SHOP_LED_MASK_URL`
- `TIKTOK_SHOP_SMART_MIRROR_URL`
- `TIKTOK_SHOP_BRUSH_SET_URL`
- `TIKTOK_SHOP_RING_LIGHT_URL`
- `TIKTOK_SHOP_SKIN_SCANNER_URL`
- `TIKTOK_SHOP_HEAT_BRUSH_URL`

When a URL is present, the generated outbound CTA uses:

```html
rel="sponsored nofollow noopener noreferrer"
```

`AFFILIATE_TRACKING_BASE_URL` is reserved for the shared affiliate tracking backend as campaigns are connected.

## Guardrails

- Maya is clearly disclosed as a virtual AI creator.
- Do not invent follower counts, reviews, discounts, product tests or sales claims.
- Do not activate a shop link until the destination and current listing are verified.
- Health and skincare content must not present AI output as medical diagnosis or treatment advice.
