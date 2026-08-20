# Agent Orchestrator

The media-factory branch already had planning, persistence and revenue logic. This layer adds execution of queued jobs so one command can run a complete safe cycle.

## Cycle

```text
maintenance
   ↓
performance signals / next_actions
   ↓
plan_work
   ↓
content_jobs queue
   ↓
job_worker
   ↓
Ollama (preferred) or deterministic fallback
   ↓
job marked done / failed
   ↓
profit summary
```

The worker does **not** auto-publish, spend money, log in to third-party accounts, or change financial settings. Outputs are drafts for the next agent or human approval.

## Run on Windows

```powershell
cd backend
.venv\Scripts\Activate.ps1
python run_agent_cycle.py --model qwen3:4b
```

Run without Ollama:

```powershell
python run_agent_cycle.py --no-ollama
```

Limit planning/execution:

```powershell
python run_agent_cycle.py --plan-limit 5 --work-limit 5 --model qwen3:4b
```

## Local Ollama

Expected default endpoint:

```text
http://127.0.0.1:11434/api/generate
```

Environment overrides:

```text
OLLAMA_URL=http://127.0.0.1:11434/api/generate
OLLAMA_MODEL=qwen3:4b
```

## What is still missing

This orchestration layer executes planning jobs, but real end-to-end monetization still requires:

1. approved affiliate program credentials and tracking links;
2. live opportunity/traffic inputs;
3. a media-rendering worker for actual short-video files;
4. platform-approved publishing integrations;
5. analytics/revenue sync after publication.

Those should be attached as additional workers rather than bypassing the existing durable queue.
