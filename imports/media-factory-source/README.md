# AI Media Factory source import

This directory contains the source bundle supplied for the AI Media Factory, staged as six base64 parts because the GitHub connector used for the import only supports text-file writes.

## Integrity

Compressed archive format: `tar.xz`

Archive SHA-256:

`c9fb36364e49b5e0f92af0bfbe0bfb96a7a11b81e26fb8361b15c8de88823876`

The archive contains the intended source/text files for `media-factory/` from the uploaded bundle. Generated video/output artifacts are intentionally not included in this source archive.

## Reconstruct on Linux/macOS

From the repository root:

```bash
cat imports/media-factory-source/part-*.b64 \
  | base64 --decode \
  > /tmp/media-factory-source.tar.xz

sha256sum /tmp/media-factory-source.tar.xz

tar -xJf /tmp/media-factory-source.tar.xz -C .
```

The hash printed by `sha256sum` must match the SHA-256 above before extraction is trusted.

Then:

```bash
cd media-factory
npm install
npm test
npm run demo
```

The supplied bundle's documentation reports 113 passing tests and a demo pipeline with Remotion as the preferred renderer and an ffmpeg/Pillow fallback when Chromium is unavailable. Re-run the tests in this repository; do not treat the supplied report as a substitute for local verification.

## Safety / repository rules

- Do not commit `.env`, API keys, access tokens, passwords, OAuth secrets, or platform credentials.
- Do not add fake traffic, fake views, fake followers, click farms, proxy farms, CAPTCHA bypasses, or engagement manipulation.
- Do not deploy or merge this branch automatically.
- Publishing integrations must use official platform APIs/OAuth and require the appropriate user approval.
- Keep Maya.exe's virtual/AI disclosure and product-claim safeguards intact.

## Intended destination

After reconstruction, the source should live directly under:

`media-factory/`

on branch:

`agent/ai-media-factory`

Once the extracted source is verified and committed normally, this temporary `imports/media-factory-source/` staging directory can be removed in a follow-up commit.
