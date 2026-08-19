from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.services.media_renderer import FPS, HEIGHT, OUTPUT_ROOT, WIDTH, build_narration, split_scenes

ASSET_ROOT = Path(os.getenv("MEDIA_ASSET_DIR", "assets/media"))
DEFAULT_MUSIC = os.getenv("MEDIA_DEFAULT_MUSIC")

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part)[:80] or "campaign"


def build_shot_plan(job: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    """Create a deterministic shot plan that can later be enriched by AI providers.

    Asset priority is intentionally conservative:
    1. verified product/demo assets,
    2. approved AI/generated clips already present on disk,
    3. generated motion cards as a fallback.
    """
    narration = build_narration(job, result)
    scenes = split_scenes(narration, max_scenes=6)
    campaign = _slug(str(job.get("campaign_id") or job.get("title") or "campaign"))
    product_dir = ASSET_ROOT / "products" / campaign
    ai_dir = ASSET_ROOT / "generated" / campaign

    product_assets = _media_files(product_dir)
    ai_assets = _media_files(ai_dir)
    shots: list[dict[str, Any]] = []

    for index, scene in enumerate(scenes):
        asset: Path | None = None
        source = "motion-card"
        if index < len(product_assets):
            asset = product_assets[index]
            source = "verified-product-asset"
        elif index - len(product_assets) < len(ai_assets):
            ai_index = index - len(product_assets)
            if ai_index >= 0:
                asset = ai_assets[ai_index]
                source = "approved-generated-asset"

        shots.append(
            {
                "index": index + 1,
                "caption": scene,
                "asset": str(asset) if asset else None,
                "asset_type": _asset_type(asset) if asset else "generated-card",
                "source": source,
            }
        )
    return shots


def _media_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS | IMAGE_EXTENSIONS
    )


def _asset_type(path: Path | None) -> str:
    if path is None:
        return "generated-card"
    return "video" if path.suffix.lower() in VIDEO_EXTENSIONS else "image"


def _ffmpeg() -> str:
    value = shutil.which("ffmpeg")
    if not value:
        raise RuntimeError("FFmpeg is required for premium video rendering.")
    return value


def _escape_drawtext(value: str) -> str:
    return (
        value.replace("\\", r"\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
        .replace("%", r"\%")
        .replace("\n", " ")
    )


def _render_shot(shot: dict[str, Any], out_path: Path, duration: float) -> None:
    ffmpeg = _ffmpeg()
    caption = _escape_drawtext(str(shot.get("caption") or ""))
    asset = Path(shot["asset"]) if shot.get("asset") else None
    asset_type = shot.get("asset_type")

    common_filter = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},"
        "format=yuv420p,"
        f"drawtext=text='{caption}':fontcolor=white:fontsize=60:"
        "x=(w-text_w)/2:y=h*0.72:box=1:boxcolor=black@0.48:boxborderw=28"
    )

    if asset and asset.exists() and asset_type == "video":
        cmd = [
            ffmpeg, "-y", "-stream_loop", "-1", "-i", str(asset),
            "-t", f"{duration:.3f}", "-an", "-vf", common_filter,
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(out_path),
        ]
    elif asset and asset.exists() and asset_type == "image":
        zoom = (
            f"scale={WIDTH*2}:{HEIGHT*2}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH*2}:{HEIGHT*2},"
            f"zoompan=z='min(zoom+0.0008,1.10)':d={max(1, int(duration*FPS))}:"
            f"s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p,"
            f"drawtext=text='{caption}':fontcolor=white:fontsize=60:"
            "x=(w-text_w)/2:y=h*0.72:box=1:boxcolor=black@0.48:boxborderw=28"
        )
        cmd = [
            ffmpeg, "-y", "-loop", "1", "-i", str(asset), "-t", f"{duration:.3f}",
            "-an", "-vf", zoom, "-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", str(out_path),
        ]
    else:
        cmd = [
            ffmpeg, "-y", "-f", "lavfi", "-i",
            f"color=c=0x111117:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration:.3f}",
            "-vf",
            f"drawtext=text='{caption}':fontcolor=white:fontsize=68:"
            "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.35:boxborderw=34,"
            f"fade=t=in:st=0:d=0.3,fade=t=out:st={max(0.1, duration-0.35):.3f}:d=0.35",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(out_path),
        ]

    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Shot render failed: {proc.stderr[-1800:]}")


def _concat_clips(clips: list[Path], out_path: Path) -> None:
    concat_file = out_path.parent / "clips.txt"
    concat_file.write_text(
        "\n".join(f"file '{clip.resolve().as_posix()}'" for clip in clips), encoding="utf-8"
    )
    proc = subprocess.run(
        [_ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
         "-c", "copy", str(out_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Clip concat failed: {proc.stderr[-1800:]}")


def _mix_audio(video: Path, voice: Path | None, music: Path | None, out_path: Path) -> None:
    ffmpeg = _ffmpeg()
    inputs = ["-i", str(video)]
    filter_complex: list[str] = []
    maps = ["-map", "0:v:0"]

    if voice and voice.exists() and music and music.exists():
        inputs += ["-i", str(voice), "-stream_loop", "-1", "-i", str(music)]
        filter_complex = [
            "[1:a]volume=1.0[voice];[2:a]volume=0.10[music];"
            "[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        ]
        maps += ["-map", "[aout]"]
    elif voice and voice.exists():
        inputs += ["-i", str(voice)]
        maps += ["-map", "1:a:0"]
    elif music and music.exists():
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        filter_complex = ["[1:a]volume=0.10[aout]"]
        maps += ["-map", "[aout]"]
    else:
        shutil.copy2(video, out_path)
        return

    cmd = [ffmpeg, "-y", *inputs]
    if filter_complex:
        cmd += ["-filter_complex", filter_complex[0]]
    cmd += [*maps, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out_path)]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Audio mix failed: {proc.stderr[-1800:]}")


def quality_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    shots = manifest.get("shots") or []
    product_count = sum(1 for shot in shots if shot.get("source") == "verified-product-asset")
    ai_count = sum(1 for shot in shots if shot.get("source") == "approved-generated-asset")
    warnings: list[str] = []
    if product_count == 0:
        warnings.append("No verified product/demo asset was supplied; product visuals should be reviewed before publishing.")
    if not manifest.get("voice_path"):
        warnings.append("No voiceover was attached.")
    if all(shot.get("source") == "motion-card" for shot in shots):
        warnings.append("All shots use fallback motion cards; add product or generated B-roll for premium quality.")
    return {
        "passed_render_checks": bool(manifest.get("video_path")),
        "verified_product_assets": product_count,
        "approved_generated_assets": ai_count,
        "warnings": warnings,
        "human_review_required": True,
    }


def render_premium_video(
    job: dict[str, Any],
    result: dict[str, Any],
    *,
    voice_path: str | None = None,
    music_path: str | None = None,
) -> dict[str, Any]:
    job_id = str(job.get("id") or "preview")
    out_dir = OUTPUT_ROOT / job_id / "premium"
    out_dir.mkdir(parents=True, exist_ok=True)

    shots = build_shot_plan(job, result)
    total_duration = max(12.0, min(60.0, len(build_narration(job, result).split()) / 2.6))
    shot_duration = total_duration / max(1, len(shots))
    clips: list[Path] = []
    for shot in shots:
        clip = out_dir / f"shot-{int(shot['index']):02d}.mp4"
        _render_shot(shot, clip, shot_duration)
        clips.append(clip)

    silent = out_dir / "video-silent.mp4"
    _concat_clips(clips, silent)
    final = out_dir / "video-premium.mp4"

    voice = Path(voice_path) if voice_path else None
    music_value = music_path or DEFAULT_MUSIC
    music = Path(music_value) if music_value else None
    _mix_audio(silent, voice, music, final)

    manifest: dict[str, Any] = {
        "video_path": str(final),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "duration_seconds": round(total_duration, 2),
        "shots": shots,
        "voice_path": str(voice) if voice and voice.exists() else None,
        "music_path": str(music) if music and music.exists() else None,
        "visual_policy": "verified-product-first",
        "status": "premium-rendered-awaiting-approval",
    }
    manifest["quality_gate"] = quality_gate(manifest)
    (out_dir / "premium-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
