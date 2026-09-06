from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VideoJob:
    campaign: str
    title: str
    script: str
    avatar_image: str
    voice_audio: str
    output: str
    aspect_ratio: str = "9:16"
    resolution: str = "720x1280"
    affiliate_disclosure: str = "Affiliate disclosure: I may earn a commission if you buy through my link, at no extra cost to you."


@dataclass(frozen=True)
class VideoFactoryPlan:
    job: VideoJob
    musetalk_command: list[str]
    ffmpeg_command: list[str]
    missing_tools: list[str]
    missing_inputs: list[str]

    @property
    def ready(self) -> bool:
        return not self.missing_tools and not self.missing_inputs


def load_video_job(path: str | Path) -> VideoJob:
    payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return VideoJob(**payload)


def build_plan(job: VideoJob, *, musetalk_root: str | Path = "vendor/MuseTalk") -> VideoFactoryPlan:
    musetalk_root = Path(musetalk_root)
    avatar = Path(job.avatar_image)
    audio = Path(job.voice_audio)
    output = Path(job.output)
    talking_head = output.with_name(output.stem + "-talking-head.mp4")

    missing_inputs = [str(path) for path in (avatar, audio) if not path.exists()]
    missing_tools: list[str] = []
    if shutil.which("python") is None:
        missing_tools.append("python")
    if shutil.which("ffmpeg") is None:
        missing_tools.append("ffmpeg")
    if not (musetalk_root / "scripts" / "inference.py").exists():
        missing_tools.append(f"MuseTalk checkout at {musetalk_root}")

    musetalk_command = [
        "python",
        str(musetalk_root / "scripts" / "inference.py"),
        "--source_image",
        str(avatar),
        "--audio_path",
        str(audio),
        "--output_path",
        str(talking_head),
    ]

    disclosure = job.affiliate_disclosure.replace("'", "’")
    vf = (
        "scale=720:1280:force_original_aspect_ratio=decrease,"
        "pad=720:1280:(ow-iw)/2:(oh-ih)/2,"
        f"drawtext=text='{disclosure}':x=(w-text_w)/2:y=h-120:"
        "fontsize=28:box=1:boxborderw=12"
    )
    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-i",
        str(talking_head),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output),
    ]

    return VideoFactoryPlan(
        job=job,
        musetalk_command=musetalk_command,
        ffmpeg_command=ffmpeg_command,
        missing_tools=missing_tools,
        missing_inputs=missing_inputs,
    )


def plan_to_dict(plan: VideoFactoryPlan) -> dict[str, Any]:
    return {
        "ready": plan.ready,
        "job": asdict(plan.job),
        "missing_tools": plan.missing_tools,
        "missing_inputs": plan.missing_inputs,
        "steps": [
            {"name": "musetalk", "command": plan.musetalk_command},
            {"name": "compose", "command": plan.ffmpeg_command},
        ],
    }
