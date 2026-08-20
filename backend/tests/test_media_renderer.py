from app.services.media_renderer import build_narration, split_scenes


def test_build_narration_includes_title_and_disclosure():
    text = build_narration(
        {"title": "AI tool comparison", "job_type": "traffic-plan"},
        {"hook": "Save time", "script": ["Show the problem", "Show the solution"]},
    )
    assert "AI tool comparison" in text
    assert "Affiliate links may earn a commission" in text


def test_split_scenes_returns_vertical_video_cards():
    scenes = split_scenes(
        "This is a short example narration that should become several readable video cards "
        "for a vertical social media draft without requiring any network access during tests."
    )
    assert 1 <= len(scenes) <= 5
    assert all(scene.strip() for scene in scenes)
