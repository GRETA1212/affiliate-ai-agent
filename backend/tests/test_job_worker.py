from app.services.job_worker import _fallback_result


def test_launch_checklist_fallback_preserves_requirements():
    result = _fallback_result(
        {
            "job_type": "launch-checklist",
            "title": "Prepare campaign",
            "brief": {"requirements": ["tracking URL", "disclosure"]},
        }
    )
    assert result["status"] == "awaiting-human-approval"
    assert result["checklist"] == ["tracking URL", "disclosure"]


def test_traffic_plan_fallback_creates_channel_tasks():
    result = _fallback_result(
        {
            "job_type": "traffic-plan",
            "title": "Create traffic plan",
            "brief": {"channels": ["youtube", "social"]},
        }
    )
    assert result["status"] == "draft-only"
    assert result["content_tasks"] == [
        "Create one buyer-intent asset for youtube",
        "Create one buyer-intent asset for social",
    ]


def test_unknown_job_never_claims_publish_action():
    result = _fallback_result(
        {"job_type": "unknown", "title": "Unknown", "brief": {"publish": True}}
    )
    assert result["status"] == "draft-only"
