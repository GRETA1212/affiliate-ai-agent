from app.services.premium_video import quality_gate


def test_quality_gate_warns_when_all_visuals_are_fallbacks():
    manifest = {
        "video_path": "outputs/media/test/premium/video-premium.mp4",
        "voice_path": None,
        "shots": [
            {"source": "motion-card"},
            {"source": "motion-card"},
        ],
    }
    gate = quality_gate(manifest)
    assert gate["passed_render_checks"] is True
    assert gate["verified_product_assets"] == 0
    assert gate["human_review_required"] is True
    assert len(gate["warnings"]) >= 2


def test_quality_gate_counts_verified_and_generated_assets():
    manifest = {
        "video_path": "outputs/media/test/premium/video-premium.mp4",
        "voice_path": "outputs/media/test/voice.mp3",
        "shots": [
            {"source": "verified-product-asset"},
            {"source": "approved-generated-asset"},
            {"source": "motion-card"},
        ],
    }
    gate = quality_gate(manifest)
    assert gate["verified_product_assets"] == 1
    assert gate["approved_generated_assets"] == 1
    assert not any("No voiceover" in warning for warning in gate["warnings"])
