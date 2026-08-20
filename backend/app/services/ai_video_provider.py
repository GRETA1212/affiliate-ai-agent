from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from app.services.premium_video import ASSET_ROOT, _slug

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
AI_VIDEO_PROVIDER = os.getenv("AI_VIDEO_PROVIDER", "disabled").strip().lower()
VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-fast-generate-preview").strip()
VEO_BASE_URL = os.getenv("VEO_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
VEO_POLL_SECONDS = float(os.getenv("VEO_POLL_SECONDS", "10"))
VEO_TIMEOUT_SECONDS = float(os.getenv("VEO_TIMEOUT_SECONDS", "420"))
VEO_MAX_CLIPS = max(0, int(os.getenv("VEO_MAX_CLIPS", "2")))


class AIVideoProviderError(RuntimeError):
    pass


def provider_enabled() -> bool:
    return AI_VIDEO_PROVIDER in {"veo", "gemini-veo"} and bool(GEMINI_API_KEY)


def _scene_texts(job: dict[str, Any], result: dict[str, Any], max_clips: int) -> list[str]:
    script = result.get("script")
    values: list[str] = []
    if isinstance(script, list):
        values = [str(item).strip() for item in script if str(item).strip()]
    elif isinstance(script, str) and script.strip():
        values = [part.strip() for part in script.split(".") if part.strip()]

    hook = str(result.get("hook") or job.get("title") or "").strip()
    if hook:
        values.insert(0, hook)

    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped[:max_clips]


def _prompt(scene: str, job: dict[str, Any]) -> str:
    title = str(job.get("title") or "affiliate product story").strip()
    return (
        "Create a photorealistic vertical social-media B-roll shot for an affiliate video. "
        "Portrait 9:16 composition, premium commercial cinematography, natural lighting, "
        "realistic human motion and physics, handheld-but-stable creator aesthetic, shallow "
        "depth of field where appropriate. Do not show logos, product packaging, prices, "
        "claims, text overlays, watermarks, or UI unless supplied as verified assets. "
        "Do not invent a product appearance. Keep the shot generic enough to cut beside real "
        f"verified product footage. Campaign context: {title}. Scene intent: {scene}."
    )


def _headers() -> dict[str, str]:
    return {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}


def _start_generation(prompt: str) -> str:
    url = f"{VEO_BASE_URL}/models/{VEO_MODEL}:predictLongRunning"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "numberOfVideos": 1,
            "aspectRatio": "9:16",
            "resolution": "1080p",
            "negativePrompt": (
                "cartoon, illustration, distorted hands, malformed fingers, duplicated limbs, "
                "warped face, unreadable text, logos, watermark, fake packaging, product label"
            ),
        },
    }
    response = httpx.post(url, headers=_headers(), json=payload, timeout=60.0)
    response.raise_for_status()
    name = str(response.json().get("name") or "").strip()
    if not name:
        raise AIVideoProviderError("Veo did not return an operation name.")
    return name


def _wait_for_video(operation_name: str) -> str:
    deadline = time.monotonic() + VEO_TIMEOUT_SECONDS
    url = f"{VEO_BASE_URL}/{operation_name}"
    while time.monotonic() < deadline:
        response = httpx.get(url, headers={"x-goog-api-key": GEMINI_API_KEY}, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        if data.get("done") is True:
            error = data.get("error")
            if error:
                raise AIVideoProviderError(f"Veo generation failed: {error}")
            samples = (
                data.get("response", {})
                .get("generateVideoResponse", {})
                .get("generatedSamples", [])
            )
            if not samples:
                raise AIVideoProviderError("Veo completed without a generated sample.")
            uri = str(samples[0].get("video", {}).get("uri") or "").strip()
            if not uri:
                raise AIVideoProviderError("Veo completed without a download URI.")
            return uri
        time.sleep(VEO_POLL_SECONDS)
    raise AIVideoProviderError("Veo generation timed out before completion.")


def _download(uri: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream(
        "GET",
        uri,
        headers={"x-goog-api-key": GEMINI_API_KEY},
        timeout=120.0,
        follow_redirects=True,
    ) as response:
        response.raise_for_status()
        with output_path.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise AIVideoProviderError("Downloaded Veo file is empty.")


def generate_broll_for_job(
    job: dict[str, Any],
    result: dict[str, Any],
    *,
    max_clips: int | None = None,
) -> dict[str, Any]:
    """Generate optional premium B-roll and place it in the existing generated-asset folder.

    This function is intentionally opt-in because provider calls may incur charges. It does
    nothing unless AI_VIDEO_PROVIDER=veo (or gemini-veo) and GEMINI_API_KEY is configured.
    """
    limit = VEO_MAX_CLIPS if max_clips is None else max(0, max_clips)
    campaign = _slug(str(job.get("campaign_id") or job.get("title") or "campaign"))
    generated_dir = ASSET_ROOT / "generated" / campaign
    generated_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "provider": AI_VIDEO_PROVIDER,
        "model": VEO_MODEL,
        "enabled": provider_enabled(),
        "requested": 0,
        "generated": [],
        "errors": [],
        "asset_dir": str(generated_dir),
    }
    if not provider_enabled() or limit == 0:
        manifest["status"] = "disabled"
        return manifest

    scenes = _scene_texts(job, result, limit)
    manifest["requested"] = len(scenes)
    for index, scene in enumerate(scenes, start=1):
        output_path = generated_dir / f"veo-{str(job.get('id') or 'preview')}-{index:02d}.mp4"
        try:
            prompt = _prompt(scene, job)
            operation = _start_generation(prompt)
            uri = _wait_for_video(operation)
            _download(uri, output_path)
            manifest["generated"].append(
                {
                    "scene": scene,
                    "path": str(output_path),
                    "operation": operation,
                    "prompt": prompt,
                }
            )
        except (httpx.HTTPError, AIVideoProviderError, ValueError) as exc:
            manifest["errors"].append({"scene": scene, "error": str(exc)[:1000]})

    manifest["status"] = "generated" if manifest["generated"] else "no-clips-generated"
    (generated_dir / f"veo-{str(job.get('id') or 'preview')}-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest
