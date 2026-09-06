from __future__ import annotations

import json
import shutil
import subprocess
import sys
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
    musetalk_root: Path
    config_path: Path
    musetalk_result: Path
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


def _ffmpeg_bin_dir() -> str:
    ffmpeg = shutil.which("ffmpeg")
    return str(Path(ffmpeg).resolve().parent) if ffmpeg else ""


def _musetalk_python(root: Path) -> Path:
    windows = root / ".venv" / "Scripts" / "python.exe"
    posix = root / ".venv" / "bin" / "python"
    if windows.exists():
        return windows
    if posix.exists():
        return posix
    return Path(sys.executable)


def build_plan(job: VideoJob, *, musetalk_root: str | Path = "vendor/MuseTalk") -> VideoFactoryPlan:
    musetalk_root = Path(musetalk_root).resolve()
    avatar = Path(job.avatar_image).resolve()
    audio = Path(job.voice_audio).resolve()
    output = Path(job.output).resolve()
    work_dir = output.parent / ".video-factory"
    config_path = work_dir / f"{output.stem}-musetalk.yaml"
    result_dir = work_dir / "musetalk-results"
    musetalk_result = result_dir / "v15" / f"{output.stem}-talking-head.mp4"

    missing_inputs = [str(path) for path in (avatar, audio) if not path.exists()]
    missing_tools: list[str] = []
    if shutil.which("ffmpeg") is None:
        missing_tools.append("ffmpeg")
    if not (musetalk_root / "scripts" / "inference.py").exists():
        missing_tools.append(f"MuseTalk checkout at {musetalk_root}")
    if not ((musetalk_root / ".venv" / "Scripts" / "python.exe").exists() or (musetalk_root / ".venv" / "bin" / "python").exists()):
        missing_tools.append(f"MuseTalk Python environment at {musetalk_root / '.venv'}")
    for required in (
        musetalk_root / "models" / "musetalkV15" / "unet.pth",
        musetalk_root / "models" / "musetalkV15" / "musetalk.json",
    ):
        if not required.exists():
            missing_tools.append(f"MuseTalk model file {required}")

    musetalk_command = [
        str(_musetalk_python(musetalk_root)),
        "-m",
        "scripts.inference",
        "--inference_config",
        str(config_path),
        "--result_dir",
        str(result_dir),
        "--unet_model_path",
        str(musetalk_root / "models" / "musetalkV15" / "unet.pth"),
        "--unet_config",
        str(musetalk_root / "models" / "musetalkV15" / "musetalk.json"),
        "--version",
        "v15",
        "--ffmpeg_path",
        _ffmpeg_bin_dir(),
    ]

    vf = "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2"
    ffmpeg_command = [
        "ffmpeg", "-y", "-i", str(musetalk_result), "-vf", vf,
        "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(output),
    ]

    return VideoFactoryPlan(
        job=job,
        musetalk_root=musetalk_root,
        config_path=config_path,
        musetalk_result=musetalk_result,
        musetalk_command=musetalk_command,
        ffmpeg_command=ffmpeg_command,
        missing_tools=missing_tools,
        missing_inputs=missing_inputs,
    )


def _write_musetalk_config(plan: VideoFactoryPlan) -> None:
    plan.config_path.parent.mkdir(parents=True, exist_ok=True)
    avatar = str(Path(plan.job.avatar_image).resolve()).replace("\\", "/")
    audio = str(Path(plan.job.voice_audio).resolve()).replace("\\", "/")
    plan.config_path.write_text(
        "task_0:\n"
        f'  video_path: "{avatar}"\n'
        f'  audio_path: "{audio}"\n'
        f'  result_name: "{plan.musetalk_result.name}"\n',
        encoding="utf-8",
    )


def render_video(job: VideoJob, *, musetalk_root: str | Path = "vendor/MuseTalk") -> Path:
    plan = build_plan(job, musetalk_root=musetalk_root)
    if not plan.ready:
        problems = [*plan.missing_tools, *plan.missing_inputs]
        raise RuntimeError("Video Factory is not ready: " + "; ".join(problems))

    output = Path(job.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_musetalk_config(plan)
    subprocess.run(plan.musetalk_command, cwd=plan.musetalk_root, check=True)
    if not plan.musetalk_result.exists():
        raise RuntimeError(f"MuseTalk finished but expected output was not found: {plan.musetalk_result}")
    subprocess.run(plan.ffmpeg_command, check=True)
    if not output.exists():
        raise RuntimeError(f"FFmpeg finished but output was not found: {output}")
    return output


def plan_to_dict(plan: VideoFactoryPlan) -> dict[str, Any]:
    return {
        "ready": plan.ready,
        "job": asdict(plan.job),
        "missing_tools": plan.missing_tools,
        "missing_inputs": plan.missing_inputs,
        "config_path": str(plan.config_path),
        "expected_musetalk_output": str(plan.musetalk_result),
        "steps": [
            {"name": "musetalk", "command": plan.musetalk_command},
            {"name": "compose", "command": plan.ffmpeg_command},
        ],
    }
