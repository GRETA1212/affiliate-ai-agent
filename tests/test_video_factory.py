from __future__ import annotations

from pathlib import Path

from affiliate_intel.video_factory import VideoJob, build_plan, plan_to_dict


def test_video_plan_reports_missing_inputs(tmp_path: Path) -> None:
    job = VideoJob(
        campaign="taskade-small-business",
        title="Taskade Launch Video 01",
        script="Test script",
        avatar_image=str(tmp_path / "missing-avatar.png"),
        voice_audio=str(tmp_path / "missing-audio.wav"),
        output=str(tmp_path / "out.mp4"),
    )

    plan = build_plan(job, musetalk_root=tmp_path / "MuseTalk")

    assert plan.ready is False
    assert str((tmp_path / "missing-avatar.png").resolve()) in plan.missing_inputs
    assert str((tmp_path / "missing-audio.wav").resolve()) in plan.missing_inputs
    assert any("MuseTalk checkout" in item for item in plan.missing_tools)


def test_video_plan_emits_official_musetalk_and_vertical_compose_command(tmp_path: Path, monkeypatch) -> None:
    avatar = tmp_path / "avatar.png"
    audio = tmp_path / "voice.wav"
    avatar.write_bytes(b"avatar")
    audio.write_bytes(b"audio")

    musetalk = tmp_path / "MuseTalk"
    inference = musetalk / "scripts" / "inference.py"
    inference.parent.mkdir(parents=True)
    inference.write_text("# stub", encoding="utf-8")

    venv_python = musetalk / ".venv" / "Scripts" / "python.exe"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_bytes(b"")

    model_dir = musetalk / "models" / "musetalkV15"
    model_dir.mkdir(parents=True)
    (model_dir / "unet.pth").write_bytes(b"weights")
    (model_dir / "musetalk.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "affiliate_intel.video_factory.shutil.which",
        lambda name: str(tmp_path / "ffmpeg.exe") if name == "ffmpeg" else None,
    )

    job = VideoJob(
        campaign="taskade-small-business",
        title="Taskade Launch Video 01",
        script="Test script",
        avatar_image=str(avatar),
        voice_audio=str(audio),
        output=str(tmp_path / "out.mp4"),
    )
    plan = build_plan(job, musetalk_root=musetalk)
    payload = plan_to_dict(plan)

    assert payload["ready"] is True
    assert plan.musetalk_command[0].endswith("python.exe")
    assert plan.musetalk_command[1:3] == ["-m", "scripts.inference"]
    assert "--version" in plan.musetalk_command
    assert "v15" in plan.musetalk_command
    assert "scale=720:1280" in " ".join(plan.ffmpeg_command)
    assert plan.musetalk_result.name == "out-talking-head.mp4"
