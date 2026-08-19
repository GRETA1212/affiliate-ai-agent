# Affiliate AI Agent

AI-assisted affiliate opportunity research, public editorial content, campaign tracking, CJ/Impact commission sync, real revenue measurement, evidence-based campaign recommendations, and local short-form video production.

## Current system — orchestrated media factory

The orchestrated branch adds a durable execution worker and premium media pipeline on top of the existing business/revenue stack.

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

The repository has three distinct applications plus the media worker:

- `website/` — public, SEO-oriented editorial site;
- `frontend/` — private research, campaign and performance dashboard;
- `backend/` — opportunity research, tracking redirects, CJ/Impact sync, SQLite revenue, performance advisor and orchestration workers;
- `backend/app/services/premium_video.py` — product-first premium short-video assembler.

## Run the private system locally

Backend:

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000 --env-file ../.env
```

Dashboard:

```bash
cd frontend
npm install
npm run dev
```

Open the dashboard at `http://localhost:5173` and API docs at `http://localhost:8000/docs`.

## Run one complete agent cycle

Make sure Ollama and FFmpeg are available, then:

```bash
cd backend
python run_agent_cycle.py --model qwen3:4b
```

The cycle runs maintenance, plans revenue-focused work, executes queued jobs, creates draft media for eligible jobs and reports real recorded profit.

## Premium video inputs

The premium renderer intentionally prefers real product/demo evidence over generated visuals.

Default folders:

```text
assets/media/products/<campaign-slug>/
assets/media/generated/<campaign-slug>/
```

Put approved product screenshots, vendor clips or screen recordings in the product folder. Put reviewed AI B-roll, digital-human clips, Unreal/MetaHuman renders or Maya renders in the generated folder.

The renderer accepts MP4/MOV/M4V/WebM and JPG/JPEG/PNG/WebP. It creates:

```text
outputs/media/<job-id>/premium/video-premium.mp4
```

See `docs/PREMIUM_VIDEO_PIPELINE.md` for the complete asset contract and quality-gate rules.

## Optional licensed music

```text
MEDIA_DEFAULT_MUSIC=C:\path\to\licensed-track.mp3
```

Music is mixed quietly under narration. Do not feed unlicensed copyrighted music into automated publishing.

## Private credentials

```text
CJ_API_TOKEN=
CJ_WEBSITE_ID=
CJ_PUBLISHER_ID=
CJ_LINK_SEARCH_URL=https://link-search.api.cj.com/v2/link-search
CJ_COMMISSION_API_URL=https://commissions.api.cj.com/query

IMPACT_ACCOUNT_SID=
IMPACT_AUTH_TOKEN=
IMPACT_API_BASE_URL=https://api.impact.com

YOUTUBE_API_KEY=
AFFILIATE_DB_PATH=data/affiliate.db
VITE_API_BASE_URL=http://localhost:8000

OLLAMA_MODEL=qwen3:4b
OLLAMA_URL=http://127.0.0.1:11434/api/generate
MEDIA_ASSET_DIR=assets/media
MEDIA_OUTPUT_DIR=outputs/media
```

Do not commit `.env` or paste account secrets into public issues, articles or source files.

## Safety boundary

The orchestrator can research, score, draft, queue, render and analyse. It does not automatically publish, spend money, log into financial accounts or fabricate revenue. Publishing and spending remain explicit approval steps.

## Current media quality level

With only fallback assets, the renderer produces a real vertical MP4 with narration and captions. With real product media and approved generated clips, it assembles a much richer short-form video. The system does not yet call Veo, MetaHuman/Unreal or Maya directly; those should be provider workers that output approved clips into the generated-assets contract.

## Next roadmap

1. Add a provider worker for high-realism AI B-roll.
2. Add a persistent digital-human worker (MetaHuman/Unreal or equivalent).
3. Add screen-demo capture for software offers.
4. Add licensed music/SFX selection.
5. Add visual QA for faces, hands, logos, product identity and caption safe-zones.
6. Add approved YouTube/TikTok publishing connectors.
7. Feed views, qualified clicks, conversions, EPC and revenue back into creative decisions.
