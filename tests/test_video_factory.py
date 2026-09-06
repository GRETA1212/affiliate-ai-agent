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
    assert str(tmp_path / "missing-avatar.png") in plan.missing_inputs
    assert str(tmp_path / "missing-audio.wav") in plan.missing_inputs
    assert any("MuseTalk checkout" in item for item in plan.missing_tools)


def test_video_plan_emits_vertical_compose_command(tmp_path: Path, monkeypatch) -> None:
    avatar = tmp_path / "avatar.png"
    audio = tmp_path / "voice.wav"
    avatar.write_bytes(b"avatar")
    audio.write_bytes(b"audio")
    musetalk = tmp_path / "MuseTalk"
    inference = musetalk / "scripts" / "inference.py"
    inference.parent.mkdir(parents=True)
    inference.write_text("# stub", encoding="utf-8")

    monkeypatch.setattr("affiliate_intel.video_factory.shutil.which", lambda _: "found")

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
    assert "scale=720:1280" in " ".join(plan.ffmpeg_command)
    assert plan.musetalk_command[0] == "python"
