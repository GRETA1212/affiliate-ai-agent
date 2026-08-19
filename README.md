# Affiliate AI Agent

AI-assisted affiliate opportunity research, public editorial content, campaign tracking, CJ/Impact commission sync, real revenue measurement, evidence-based campaign recommendations, and local short-form video production.

## Current system — orchestrated premium media factory

```text
opportunity + campaign data
        ↓
performance advisor / planner
        ↓
durable content-job queue
        ↓
Ollama execution worker
        ↓
hook + script + shot intent
        ↓
verified product/demo assets
        ↓
optional Veo 3.1 portrait B-roll
        ↓
approved AI / creator / B-roll clips
        ↓
voice + captions + optional licensed music
        ↓
FFmpeg premium 1080×1920 H.264 render
        ↓
quality gate
        ↓
human approval
```

The repository has three applications plus media workers:

- `website/` — public editorial site;
- `frontend/` — private research/campaign/performance dashboard;
- `backend/` — opportunity research, tracking, affiliate-network sync, revenue logic and orchestration;
- `backend/app/services/ai_video_provider.py` — optional Veo 3.1 B-roll provider;
- `backend/app/services/premium_video.py` — product-first premium short-video assembler.

## Run locally

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python run_agent_cycle.py --model qwen3:4b
```

FFmpeg/ffprobe must be on PATH. Ollama is recommended for local scripts. The preferred review output is:

```text
outputs/media/<job-id>/premium/video-premium.mp4
```

## Premium video inputs

Real product/demo evidence has priority:

```text
assets/media/products/<campaign-slug>/
assets/media/generated/<campaign-slug>/
```

Product screenshots, vendor clips and screen recordings belong in `products`. Reviewed AI B-roll, digital-human clips, Unreal/MetaHuman renders and Maya renders belong in `generated`.

## Optional Veo 3.1 B-roll

The media factory can now call Gemini/Veo and request high-realism portrait `9:16` B-roll before final assembly. This is **disabled by default** because external generation may incur charges.

Explicitly enable it in `.env` only when you want billable AI-video generation:

```text
AI_VIDEO_PROVIDER=veo
GEMINI_API_KEY=<private key>
VEO_MODEL=veo-3.1-fast-generate-preview
VEO_MAX_CLIPS=2
```

To guarantee no Veo generation calls:

```text
AI_VIDEO_PROVIDER=disabled
```

Generated prompts prohibit invented product appearance, fake packaging, logos, prices, labels, watermarks and unsupported claims. Product-specific identity comes from verified real assets.

Generated clips are written to:

```text
assets/media/generated/<campaign-slug>/
  veo-<job-id>-01.mp4
  veo-<job-id>-02.mp4
  veo-<job-id>-manifest.json
```

The premium renderer then automatically picks those files up.

## Optional licensed music

```text
MEDIA_DEFAULT_MUSIC=C:\path\to\licensed-track.mp3
```

## Private configuration

```text
CJ_API_TOKEN=
CJ_WEBSITE_ID=
CJ_PUBLISHER_ID=
IMPACT_ACCOUNT_SID=
IMPACT_AUTH_TOKEN=
YOUTUBE_API_KEY=
AFFILIATE_DB_PATH=data/affiliate.db
VITE_API_BASE_URL=http://localhost:8000

OLLAMA_MODEL=qwen3:4b
OLLAMA_URL=http://127.0.0.1:11434/api/generate
EDGE_TTS_VOICE=en-US-AriaNeural
MEDIA_ASSET_DIR=assets/media
MEDIA_OUTPUT_DIR=outputs/media
MEDIA_DEFAULT_MUSIC=

AI_VIDEO_PROVIDER=disabled
GEMINI_API_KEY=
VEO_MODEL=veo-3.1-fast-generate-preview
VEO_MAX_CLIPS=2
```

Do not commit `.env` or paste private credentials into source files or issues.

## Safety boundary

The orchestrator can research, score, draft, queue, render and analyse. It does not automatically publish or spend money. Paid AI-video generation requires explicit provider configuration, and every premium video remains human-review-required before publishing.

## Next roadmap

1. Persistent digital-human worker (MetaHuman/Unreal or approved equivalent).
2. Real screen-demo capture worker for software offers.
3. Stronger visual QA for faces, hands, text, logos, product identity and safe-zones.
4. Approved YouTube/TikTok publishing connectors after review.
5. Analytics feedback from views → clicks → conversions → EPC → profit.

See `docs/PREMIUM_VIDEO_PIPELINE.md` for the complete asset contract and provider design.
