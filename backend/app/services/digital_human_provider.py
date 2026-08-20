from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.services.premium_video import ASSET_ROOT, _slug

CREATOR_PROVIDER = os.getenv("DIGITAL_HUMAN_PROVIDER", "disabled").strip().lower()
UNREAL_EDITOR_CMD = os.getenv("UNREAL_EDITOR_CMD", "").strip()
UNREAL_PROJECT = os.getenv("UNREAL_PROJECT", "").strip()
UNREAL_LEVEL_SEQUENCE = os.getenv("UNREAL_LEVEL_SEQUENCE", "").strip()
UNREAL_MOVIE_PIPELINE_CONFIG = os.getenv("UNREAL_MOVIE_PIPELINE_CONFIG", "").strip()
CREATOR_ID = os.getenv("DIGITAL_HUMAN_ID", "maya-creator-v1").strip() or "maya-creator-v1"


def provider_ready() -> tuple[bool, str]:
    if CREATOR_PROVIDER in {"", "disabled", "none"}:
        return False, "digital-human provider disabled"
    if CREATOR_PROVIDER != "unreal-metahuman":
        return False, f"unsupported digital-human provider: {CREATOR_PROVIDER}"
    required = {
        "UNREAL_EDITOR_CMD": UNREAL_EDITOR_CMD,
        "UNREAL_PROJECT": UNREAL_PROJECT,
        "UNREAL_LEVEL_SEQUENCE": UNREAL_LEVEL_SEQUENCE,
        "UNREAL_MOVIE_PIPELINE_CONFIG": UNREAL_MOVIE_PIPELINE_CONFIG,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        return False, "missing " + ", ".join(missing)
    return True, "ready"


def build_creator_prompt(job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    script = result.get("script") or []
    if isinstance(script, str):
        script_lines = [script]
    else:
        script_lines = [str(item).strip() for item in script if str(item).strip()]
    return {
        "creator_id": CREATOR_ID,
        "campaign_id": job.get("campaign_id"),
        "title": job.get("title"),
        "hook": result.get("hook"),
        "script": script_lines[:6],
        "cta": result.get("cta"),
        "style": {
            "framing": "vertical creator close-up / medium shot",
            "tone": "natural, conversational, non-deceptive",
            "identity_rule": "reuse the same approved MetaHuman identity for every render",
            "product_rule": "do not invent product appearance; product visuals come from verified product assets",
        },
    }


def render_creator_clip(job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    ready, reason = provider_ready()
    if not ready:
        return {"status": "skipped", "provider": CREATOR_PROVIDER or "disabled", "reason": reason}

    campaign = _slug(str(job.get("campaign_id") or job.get("title") or "campaign"))
    out_dir = ASSET_ROOT / "generated" / campaign
    out_dir.mkdir(parents=True, exist_ok=True)
    request_path = out_dir / "creator-request.json"
    request_path.write_text(json.dumps(build_creator_prompt(job, result), indent=2), encoding="utf-8")

    editor = shutil.which(UNREAL_EDITOR_CMD) or UNREAL_EDITOR_CMD
    output_path = out_dir / f"00-{CREATOR_ID}.mp4"

    # This adapter expects the Unreal project to already contain:
    # 1) the approved recurring MetaHuman,
    # 2) a configured Level Sequence,
    # 3) a Movie Render Queue config,
    # 4) project-side automation that reads CREATOR_REQUEST_PATH and renders to CREATOR_OUTPUT_PATH.
    env = os.environ.copy()
    env["CREATOR_REQUEST_PATH"] = str(request_path.resolve())
    env["CREATOR_OUTPUT_PATH"] = str(output_path.resolve())
    cmd = [
        editor,
        UNREAL_PROJECT,
        "-game",
        f"-LevelSequence={UNREAL_LEVEL_SEQUENCE}",
        f"-MoviePipelineConfig={UNREAL_MOVIE_PIPELINE_CONFIG}",
        "-unattended",
        "-nosplash",
        "-NoSound",
        "-log",
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        return {
            "status": "failed",
            "provider": CREATOR_PROVIDER,
            "request_path": str(request_path),
            "error": proc.stderr[-2500:] or proc.stdout[-2500:],
        }
    if not output_path.exists() or output_path.stat().st_size == 0:
        return {
            "status": "failed",
            "provider": CREATOR_PROVIDER,
            "request_path": str(request_path),
            "error": "Unreal command completed but no creator MP4 was produced.",
        }
    return {
        "status": "generated-awaiting-review",
        "provider": CREATOR_PROVIDER,
        "creator_id": CREATOR_ID,
        "video_path": str(output_path),
        "request_path": str(request_path),
        "verified_product_evidence": False,
        "human_review_required": True,
    }
