from app.services import ai_video_provider


def test_provider_disabled_without_explicit_configuration(monkeypatch):
    monkeypatch.setattr(ai_video_provider, "AI_VIDEO_PROVIDER", "disabled")
    monkeypatch.setattr(ai_video_provider, "GEMINI_API_KEY", "")
    assert ai_video_provider.provider_enabled() is False


def test_scene_texts_caps_requested_clips():
    job = {"title": "Example campaign"}
    result = {
        "hook": "Hook",
        "script": ["Beat one", "Beat two", "Beat three"],
    }
    assert ai_video_provider._scene_texts(job, result, 2) == ["Hook", "Beat one"]


def test_prompt_forbids_invented_product_appearance():
    prompt = ai_video_provider._prompt("Show the problem", {"title": "Example"})
    assert "Do not invent a product appearance" in prompt
    assert "Portrait 9:16" in prompt
