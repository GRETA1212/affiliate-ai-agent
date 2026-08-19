from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any

try:
    import edge_tts
except ImportError:  # optional at runtime; silent fallback still renders video
    edge_tts = None


OUTPUT_ROOT = Path(os.getenv("MEDIA_OUTPUT_DIR", "outputs/media"))
DEFAULT_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")
WIDTH = 1080
HEIGHT = 1920
FPS = 30


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (list, tuple)):
        return " ".join(_clean_text(item) for item in value if _clean_text(item))
    if isinstance(value, dict):
        return " ".join(
            f"{key}: {_clean_text(item)}" for key, item in value.items() if _clean_text(item)
        )
    return str(value)


def build_narration(job: dict[str, Any], result: dict[str, Any]) -> str:
    title = _clean_text(job.get("title")) or "Affiliate opportunity update"
    job_type = _clean_text(job.get("job_type"))
    body = _clean_text(result)
    if len(body) > 900:
        body = body[:897].rstrip() + "..."
    disclosure = "This is informational content. Affiliate links may earn a commission at no extra cost to you."
    return " ".join(part for part in [title, job_type, body, disclosure] if part)


def split_scenes(text: str, max_scenes: int = 5) -> list[str]:
    words = text.split()
    if not words:
        return ["Affiliate content draft"]
    target = max(10, min(24, (len(words) + max_scenes - 1) // max_scenes))
    scenes: list[str] = []
    for start in range(0, len(words), target):
        chunk = " ".join(words[start : start + target])
        scenes.append("\n".join(textwrap.wrap(chunk, width=26)))
        if len(scenes) >= max_scenes:
            break
    return scenes


async def _synthesize(text: str, output_path: Path, voice: str) -> bool:
    if edge_tts is None:
        return False
    try:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate="+5%")
        await communicate.save(str(output_path))
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception:
        return False


def _probe_duration(media_path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        return float(proc.stdout.strip()) if proc.returncode == 0 else None
    except ValueError:
        return None


def _font_path() -> str | None:
    candidates = [
        os.getenv("VIDEO_FONT_PATH"),
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def _render_ffmpeg(
    *,
    scenes: list[str],
    scene_files: list[Path],
    audio_path: Path | None,
    output_path: Path,
    duration: float,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to render MP4 video. Install ffmpeg and ensure it is on PATH.")

    duration = max(8.0, min(duration, 90.0))
    per_scene = duration / len(scenes)
    font = _font_path()
    filters: list[str] = []

    for index, text_file in enumerate(scene_files):
        start = index * per_scene
        end = duration if index == len(scene_files) - 1 else (index + 1) * per_scene
        args = [
            f"textfile='{_escape_filter_path(text_file)}'",
            "fontcolor=white",
            "fontsize=70",
            "line_spacing=18",
            "x=(w-text_w)/2",
            "y=(h-text_h)/2",
            "box=1",
            "boxcolor=black@0.45",
            "boxborderw=35",
            f"enable='between(t,{start:.3f},{end:.3f})'",
        ]
        if font:
            args.insert(0, f"fontfile='{_escape_filter_path(Path(font))}'")
        filters.append("drawtext=" + ":".join(args))

    video_filter = ",".join(filters)
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x101014:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration:.3f}",
    ]
    if audio_path and audio_path.exists():
        cmd += ["-i", str(audio_path)]
    cmd += ["-vf", video_filter, "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p"]
    if audio_path and audio_path.exists():
        cmd += ["-c:a", "aac", "-b:a", "160k", "-shortest"]
    else:
        cmd += ["-an", "-t", f"{duration:.3f}"]
    cmd += ["-movflags", "+faststart", str(output_path)]

    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed: {proc.stderr[-2000:]}")


def render_job_video(
    job: dict[str, Any],
    result: dict[str, Any],
    *,
    voice: str = DEFAULT_VOICE,
) -> dict[str, Any]:
    job_id = str(job.get("id") or "preview")
    output_dir = OUTPUT_ROOT / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    narration = build_narration(job, result)
    scenes = split_scenes(narration)
    script_path = output_dir / "script.txt"
    script_path.write_text(narration, encoding="utf-8")

    scene_files: list[Path] = []
    for index, scene in enumerate(scenes, start=1):
        path = output_dir / f"scene-{index:02d}.txt"
        path.write_text(scene, encoding="utf-8")
        scene_files.append(path)

    audio_path = output_dir / "voice.mp3"
    tts_ok = asyncio.run(_synthesize(narration, audio_path, voice))
    duration = _probe_duration(audio_path) if tts_ok else None
    if duration is None:
        duration = max(12.0, len(narration.split()) / 2.7)

    video_path = output_dir / "video.mp4"
    _render_ffmpeg(
        scenes=scenes,
        scene_files=scene_files,
        audio_path=audio_path if tts_ok else None,
        output_path=video_path,
        duration=duration,
    )

    manifest = {
        "video_path": str(video_path),
        "script_path": str(script_path),
        "audio_path": str(audio_path) if tts_ok else None,
        "voice": voice if tts_ok else None,
        "tts": "edge-tts" if tts_ok else "silent-fallback",
        "format": "mp4",
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "duration_seconds": round(float(duration), 2),
        "scene_count": len(scenes),
        "status": "rendered-awaiting-approval",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
