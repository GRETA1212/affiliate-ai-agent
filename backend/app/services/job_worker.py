import json
import os
from typing import Any

import httpx

from app.services.business_controller import claim_next_job, complete_job, fail_job


DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")


SYSTEM_RULES = """You are the execution worker for an affiliate content system.
Create useful, factual, non-deceptive output from the supplied job brief.
Never invent product claims, prices, commissions, performance, reviews, or guarantees.
Never publish content, spend money, log in to third-party accounts, or change financial settings.
Return JSON only.
"""


def _fallback_result(job: dict[str, Any]) -> dict[str, Any]:
    brief = job.get("brief") or {}
    job_type = job.get("job_type", "generic")

    if job_type == "launch-checklist":
        return {
            "mode": "fallback",
            "job_type": job_type,
            "checklist": brief.get("requirements", []),
            "status": "awaiting-human-approval",
        }
    if job_type == "traffic-plan":
        channels = brief.get("channels", ["search", "youtube", "social"])
        return {
            "mode": "fallback",
            "job_type": job_type,
            "channels": channels,
            "content_tasks": [
                f"Create one buyer-intent asset for {channel}" for channel in channels
            ],
            "status": "draft-only",
        }
    if job_type == "experiment-plan":
        variables = brief.get("variables", [])
        primary = variables[0] if variables else "headline"
        return {
            "mode": "fallback",
            "job_type": job_type,
            "experiment": {
                "primary_variable": primary,
                "variant_a": "control",
                "variant_b": "alternative",
                "rule": brief.get("rule", "change one primary variable at a time"),
            },
        }
    if job_type == "rework-analysis":
        return {
            "mode": "fallback",
            "job_type": job_type,
            "diagnostic_checks": brief.get("check", []),
            "status": "requires-review-before-more-traffic",
        }
    if job_type == "scale-plan":
        return {
            "mode": "fallback",
            "job_type": job_type,
            "actions": brief.get("actions", []),
            "status": "draft-only",
        }

    return {
        "mode": "fallback",
        "job_type": job_type,
        "title": job.get("title"),
        "brief": brief,
        "status": "draft-only",
    }


def _ollama_result(job: dict[str, Any], model: str) -> dict[str, Any] | None:
    prompt = (
        SYSTEM_RULES
        + "\nJOB:\n"
        + json.dumps(
            {
                "job_type": job.get("job_type"),
                "title": job.get("title"),
                "brief": job.get("brief") or {},
                "campaign_id": job.get("campaign_id"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\nProduce an actionable draft suitable for the next agent or human reviewer."
    )
    try:
        response = httpx.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=90.0,
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        if not text:
            return None
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed.setdefault("mode", "ollama")
            parsed.setdefault("model", model)
            return parsed
    except (httpx.HTTPError, json.JSONDecodeError, ValueError):
        return None
    return None


def execute_next_job(*, model: str = DEFAULT_MODEL, use_ollama: bool = True) -> dict[str, Any] | None:
    job = claim_next_job()
    if job is None:
        return None

    try:
        result = _ollama_result(job, model) if use_ollama else None
        if result is None:
            result = _fallback_result(job)
        complete_job(job["id"], result)
        return {"job_id": job["id"], "job_type": job["job_type"], "result": result}
    except Exception as exc:  # keep the durable queue from getting stuck in running
        fail_job(job["id"], str(exc))
        return {"job_id": job["id"], "job_type": job["job_type"], "error": str(exc)}


def drain_jobs(
    *,
    limit: int = 10,
    model: str = DEFAULT_MODEL,
    use_ollama: bool = True,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for _ in range(limit):
        result = execute_next_job(model=model, use_ollama=use_ollama)
        if result is None:
            break
        results.append(result)
    return results
