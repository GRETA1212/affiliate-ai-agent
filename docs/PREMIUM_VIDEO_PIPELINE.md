# Premium Video Pipeline

The premium renderer is designed around one rule: **real/verified product evidence beats invented product visuals**.

## Production order

```text
campaign / opportunity
      ↓
Ollama script + shot intent
      ↓
verified product/demo assets
      ↓
optional Veo 3.1 portrait B-roll
      ↓
approved AI/creator/B-roll clips
      ↓
motion-card fallback
      ↓
voiceover + captions + music
      ↓
1080×1920 H.264 MP4
      ↓
quality gate
      ↓
human approval
```

## Asset folders

Set `MEDIA_ASSET_DIR` or use the default `assets/media` path from the backend working directory.

Real product assets:

```text
assets/media/products/<campaign-slug>/
  01-product-demo.mp4
  02-dashboard.png
  03-feature-screen.mp4
```

Approved generated clips:

```text
assets/media/generated/<campaign-slug>/
  01-lifestyle-broll.mp4
  02-creator-shot.mp4
  03-transition.mp4
```

Supported visual files: MP4, MOV, M4V, WebM, JPG, JPEG, PNG and WebP.

## Veo 3.1 B-roll worker

`app/services/ai_video_provider.py` implements the first external high-realism worker. It uses the Gemini API long-running video-generation flow, requests portrait `9:16` clips, polls the operation, downloads the completed MP4, and writes it into the same generated-assets contract used by the premium renderer.

The provider is disabled by default because generation may incur external charges:

```text
AI_VIDEO_PROVIDER=disabled
GEMINI_API_KEY=
```

Explicitly enable it only when billable generation is intended:

```text
AI_VIDEO_PROVIDER=veo
GEMINI_API_KEY=<private key>
VEO_MODEL=veo-3.1-fast-generate-preview
VEO_MAX_CLIPS=2
VEO_POLL_SECONDS=10
VEO_TIMEOUT_SECONDS=420
```

When the provider is disabled or the key is absent, the worker makes no Veo generation request and the media pipeline continues with existing product/generated assets and local fallback rendering.

Generated B-roll is intentionally **not** treated as verified product evidence. Prompts prohibit invented product appearance, fake packaging, logos, prices, labels, watermarks and unsupported claims. Product-specific visuals should come from real vendor/product/demo assets.

Provider outputs:

```text
assets/media/generated/<campaign-slug>/
  veo-<job-id>-01.mp4
  veo-<job-id>-02.mp4
  veo-<job-id>-manifest.json
```

The manifest records the source scene, generation prompt, operation identifier, output path and any errors.

## Provider architecture

Provider-specific workers create or capture media and place it into the shared asset folders. The premium renderer remains provider-agnostic.

- `product-asset-worker` — verified vendor/product media.
- `ai-broll-worker` — implemented with optional Veo 3.1 generation.
- `digital-human-worker` — future persistent virtual creator via MetaHuman/Unreal or approved provider.
- `screen-demo-worker` — future real software/product UI capture.
- `music-worker` — licensed background audio selection.
- `premium_video` — shot assembly, captions, narration and music.
- `qa-worker` — product identity, claims, visual artifacts, disclosure and legibility.

## Music

```text
MEDIA_DEFAULT_MUSIC=C:\path\to\licensed-track.mp3
```

Music is mixed quietly under narration.

## Output

```text
outputs/media/<job-id>/
  video.mp4
  voice.mp3
  script.txt
  manifest.json
  premium/
    shot-01.mp4
    shot-02.mp4
    ...
    video-silent.mp4
    video-premium.mp4
    premium-manifest.json
```

`video-premium.mp4` is the preferred human-review output.

## Quality gate

The premium manifest records verified product assets, approved generated assets, narration presence, fallback-card warnings and mandatory human review. A successful render is not proof that the underlying claims or product identity are correct.

## Maya vs Unreal vs generative video

Maya remains an optional specialist renderer for premium 3D product shots. MetaHuman/Unreal is a better fit for a persistent digital creator. Generative video is the fast path for realistic B-roll. All feed the same `generated/<campaign-slug>/` contract instead of creating parallel publishing systems.
