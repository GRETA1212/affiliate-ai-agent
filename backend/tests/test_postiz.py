import json
from datetime import UTC, datetime

import httpx
import pytest

from app.connectors import postiz


TEST_CONFIG = postiz.PostizConfig(
    api_key="postiz-test-key",
    base_url="https://postiz.test/public/v1",
)


def make_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_status_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTIZ_API_KEY", raising=False)
    connector = postiz.status()
    assert connector.name == "postiz"
    assert connector.configured is False


def test_list_integrations_uses_authorization_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/public/v1/integrations"
        assert request.headers["Authorization"] == "postiz-test-key"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "tiktok-1",
                    "name": "Maya.exe",
                    "identifier": "tiktok",
                    "disabled": False,
                    "profile": "maya.exe",
                }
            ],
        )

    with make_client(handler) as client:
        integrations = postiz.list_integrations(config=TEST_CONFIG, client=client)

    assert len(integrations) == 1
    assert integrations[0].identifier == "tiktok"


def test_upload_from_url_returns_media() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/public/v1/upload-from-url"
        assert json.loads(request.content) == {"url": "https://cdn.example.com/maya.mp4"}
        return httpx.Response(
            200,
            json={
                "id": "media-1",
                "name": "maya.mp4",
                "path": "https://uploads.postiz.test/maya.mp4",
            },
        )

    with make_client(handler) as client:
        media = postiz.upload_from_url(
            "https://cdn.example.com/maya.mp4",
            config=TEST_CONFIG,
            client=client,
        )

    assert media.id == "media-1"
    assert media.path.endswith("maya.mp4")


def test_upload_from_url_rejects_non_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        postiz.upload_from_url("http://localhost/maya.mp4", config=TEST_CONFIG)


def test_maya_tiktok_post_enforces_ai_disclosure_and_native_ai_flag() -> None:
    integration = postiz.PostizIntegration(
        id="tiktok-1",
        name="Maya.exe",
        identifier="tiktok",
        profile="maya.exe",
    )
    draft = postiz.build_maya_channel_post(
        integration,
        content="A makeup idea generated for Maya.",
        title="AI makeup idea",
    )

    assert "Virtual AI creator" in draft.content
    assert draft.settings["__type"] == "tiktok"
    assert draft.settings["video_made_with_ai"] is True
    assert draft.settings["content_posting_method"] == "DIRECT_POST"


def test_maya_youtube_post_uses_supported_defaults() -> None:
    integration = postiz.PostizIntegration(
        id="youtube-1",
        name="Maya.exe",
        identifier="youtube",
    )
    draft = postiz.build_maya_channel_post(
        integration,
        content="Short description",
        title="3 Things AI Got Wrong",
        youtube_visibility="unlisted",
    )

    assert draft.settings == {
        "__type": "youtube",
        "title": "3 Things AI Got Wrong",
        "type": "unlisted",
        "selfDeclaredMadeForKids": "no",
        "tags": [],
    }


def test_create_posts_builds_multi_channel_payload() -> None:
    media = postiz.PostizMedia(id="media-1", path="https://uploads.postiz.test/maya.mp4")
    posts = [
        postiz.PostizChannelPost(
            integration_id="tiktok-1",
            content="TikTok caption",
            media=[media],
            settings={"__type": "tiktok", "video_made_with_ai": True},
        ),
        postiz.PostizChannelPost(
            integration_id="youtube-1",
            content="YouTube description",
            media=[media],
            settings={"__type": "youtube", "title": "Maya video", "type": "public"},
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/public/v1/posts"
        assert body["type"] == "schedule"
        assert body["date"] == "2026-09-08T17:00:00.000Z"
        assert len(body["posts"]) == 2
        assert body["posts"][0]["value"][0]["image"] == [
            {"id": "media-1", "path": "https://uploads.postiz.test/maya.mp4"}
        ]
        return httpx.Response(
            200,
            json=[
                {"postId": "post-1", "integration": "tiktok-1"},
                {"postId": "post-2", "integration": "youtube-1"},
            ],
        )

    scheduled_at = datetime(2026, 9, 8, 17, 0, tzinfo=UTC)
    with make_client(handler) as client:
        results = postiz.create_posts(
            posts,
            mode="schedule",
            scheduled_at=scheduled_at,
            config=TEST_CONFIG,
            client=client,
        )

    assert [item.post_id for item in results] == ["post-1", "post-2"]


def test_schedule_requires_timezone_aware_datetime() -> None:
    post = postiz.PostizChannelPost(
        integration_id="tiktok-1",
        content="caption",
        settings={"__type": "tiktok"},
    )
    with pytest.raises(ValueError, match="timezone"):
        postiz.create_posts(
            [post],
            mode="schedule",
            scheduled_at=datetime(2026, 9, 8, 19, 0),
            config=TEST_CONFIG,
        )


def test_disabled_integration_is_blocked() -> None:
    integration = postiz.PostizIntegration(
        id="tiktok-1",
        name="Maya.exe",
        identifier="tiktok",
        disabled=True,
    )
    with pytest.raises(ValueError, match="disabled"):
        postiz.build_maya_channel_post(
            integration,
            content="caption",
            title="Maya",
        )
