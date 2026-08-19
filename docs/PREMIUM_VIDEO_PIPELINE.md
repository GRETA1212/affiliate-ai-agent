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

Set `MEDIA_ASSET_DIR` or use the default `backend/assets/media`-relative working path.

For a campaign slug, add real product assets here:

```text
assets/media/products/<campaign-slug>/
  01-product-demo.mp4
  02-dashboard.png
  03-feature-screen.mp4
```

Approved generated clips go here:

```text
assets/media/generated/<campaign-slug>/
  01-lifestyle-broll.mp4
  02-creator-shot.mp4
  03-transition.mp4
```

The renderer uses files in deterministic filename order.

Supported visual files:

- MP4, MOV, M4V, WebM
- JPG, JPEG, PNG, WebP

## Future high-realism providers

Do not hard-code a single provider into the business controller. Provider-specific workers should create clips and place them into the approved generated-assets folder, then the same premium renderer assembles them.

Recommended worker roles:

- `product-asset-worker` — downloads or receives approved vendor/product media.
- `ai-broll-worker` — generates realistic lifestyle/B-roll clips using the configured video provider.
- `digital-human-worker` — renders an approved recurring virtual creator through MetaHuman/Unreal or another provider.
- `screen-demo-worker` — records real software/product UI flows.
- `music-worker` — selects licensed background audio.
- `premium_video` — assembles shots, captions, narration and music.
- `qa-worker` — checks product identity, claims, visual artifacts, disclosure and legibility.

## Music

Set an optional licensed track:

```text
MEDIA_DEFAULT_MUSIC=C:\path\to\licensed-track.mp3
```

The renderer mixes music at a low level under narration.

## Output

Each job writes:

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

The manifest records:

- count of verified product assets;
- count of approved generated assets;
- warnings when no product media is present;
- warning when no voiceover is present;
- warning when all visuals are fallback motion cards;
- mandatory human review before publishing.

The quality gate does not claim that a video is truthful merely because it rendered successfully. Product identity, claims, generated humans and platform compliance still require review.

## Maya vs Unreal vs generative video

Maya is an optional specialist renderer for premium 3D product shots, not the main short-form pipeline. MetaHuman/Unreal is a better fit for a persistent digital creator. Generative video providers are better for rapid realistic B-roll. All of them should feed the same `generated/<campaign-slug>/` contract instead of creating parallel publishing systems.
