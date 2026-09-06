from pathlib import Path

import httpx
import pytest

from app.connectors.tiktok_publisher import (
    TikTokPostRequest,
    TikTokPublisher,
    TikTokPublisherConfig,
    TikTokPublisherError,
)


def make_video(tmp_path: Path, payload: bytes = b"fake-mp4") -> Path:
    path = tmp_path / "maya-v002.mp4"
    path.write_bytes(payload)
    return path


def test_request_rejects_missing_video(tmp_path: Path) -> None:
    request = TikTokPostRequest(video_path=tmp_path / "missing.mp4", caption="hello")
    with pytest.raises(TikTokPublisherError, match="does not exist"):
        request.validate()


def test_request_rejects_non_mp4(tmp_path: Path) -> None:
    path = tmp_path / "maya.mov"
    path.write_bytes(b"x")
    request = TikTokPostRequest(video_path=path, caption="hello")
    with pytest.raises(TikTokPublisherError, match="MP4 only"):
        request.validate()


def test_draft_publish_initializes_and_uploads(tmp_path: Path) -> None:
    video = make_video(tmp_path, b"12345678")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/post/publish/inbox/video/init/"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "publish_id": "pub-123",
                        "upload_url": "https://upload.example/video",
                    },
                    "error": {"code": "ok", "message": ""},
                },
            )
        if request.url.host == "upload.example":
            return httpx.Response(201)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    publisher = TikTokPublisher(
        TikTokPublisherConfig(access_token="test-token", mode="draft"),
        client=client,
    )

    result = publisher.publish(TikTokPostRequest(video_path=video, caption="Maya.exe V002"))

    assert result == {"mode": "draft", "publish_id": "pub-123", "status": "uploaded"}
    assert seen[0].headers["authorization"] == "Bearer test-token"
    assert seen[1].headers["content-range"] == "bytes 0-7/8"


def test_direct_publish_includes_post_info(tmp_path: Path) -> None:
    video = make_video(tmp_path)
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/post/publish/video/init/"):
            captured["body"] = request.read().decode()
            return httpx.Response(
                200,
                json={
                    "data": {
                        "publish_id": "pub-direct",
                        "upload_url": "https://upload.example/direct",
                    },
                    "error": {"code": "ok", "message": ""},
                },
            )
        if request.url.host == "upload.example":
            return httpx.Response(200)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    publisher = TikTokPublisher(
        TikTokPublisherConfig(access_token="test-token", mode="direct"),
        client=client,
    )

    publisher.publish(
        TikTokPostRequest(
            video_path=video,
            caption="3 Things AI Got Wrong #MayaExe",
            privacy_level="SELF_ONLY",
        )
    )

    body = str(captured["body"])
    assert "3 Things AI Got Wrong" in body
    assert "SELF_ONLY" in body


def test_api_errors_are_not_silently_accepted(tmp_path: Path) -> None:
    video = make_video(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"code": "access_token_invalid", "message": "bad token"}},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    publisher = TikTokPublisher(
        TikTokPublisherConfig(access_token="bad-token", mode="draft"),
        client=client,
    )

    with pytest.raises(TikTokPublisherError, match="access_token_invalid"):
        publisher.publish(TikTokPostRequest(video_path=video, caption="Maya"))
