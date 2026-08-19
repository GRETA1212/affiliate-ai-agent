from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict
from typing import Any

from .models import Opportunity


OLLAMA_URL = "http://localhost:11434/api/generate"


def build_content_prompt(opportunity: Opportunity) -> str:
    payout = opportunity.price * opportunity.commission_rate
    return f"""You are an affiliate short-form content strategist.

Create a compact content test pack for this opportunity:
{json.dumps(asdict(opportunity), indent=2)}
Estimated payout per sale: ${payout:.2f}

Return ONLY valid JSON with this exact shape:
{{
  "positioning": "one sentence",
  "audience": "specific buyer audience",
  "hooks": ["10 short hooks"],
  "scripts": [
    {{"title": "video title", "hook": "first line", "body": "20-35 second script", "cta": "clear non-deceptive CTA"}}
  ],
  "test_plan": ["3 concise test actions"]
}}

Rules:
- Produce exactly 10 hooks and 3 scripts.
- Do not invent discounts, earnings, guarantees, testimonials, or product claims.
- Mention that affiliate disclosure should be included when appropriate.
- Optimize for TikTok and YouTube Shorts, but do not use spam tactics.
"""


def generate_content_pack(
    opportunity: Opportunity,
    model: str = "qwen3:4b",
    url: str = OLLAMA_URL,
    timeout: int = 180,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": build_content_prompt(opportunity),
        "format": "json",
        "stream": False,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Could not reach local Ollama. Start Ollama and make sure the selected model is installed."
        ) from exc

    generated = raw.get("response", "")
    try:
        result = json.loads(generated)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Ollama returned text that was not valid JSON.") from exc

    result["model"] = model
    result["opportunity"] = opportunity.name
    return result
