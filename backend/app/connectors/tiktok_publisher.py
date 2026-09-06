from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx


TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"


class TikTokPublisherError(RuntimeError):
    """Raised when TikTok publishing cannot proceed safely."""


@dataclass(frozen=True)
class TikTokPublisherConfig:
    access_token: str
    mode: Literal["draft", "direct"] = "draft"
    api_base: str = TIKTOK_API_BASE
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "TikTokPublisherConfig":
        token = os.getenv("TIKTOK_ACCESS_TOKEN", "").strip()
        if not token:
            raise TikTokPublisherError("TIKTOK_ACCESS_TOKEN is not configured")

        mode = os.getenv("TIKTOK_PUBLISH_MODE", "draft").strip().lower()
        if mode not in {"draft", "direct"}:
            raise TikTokPublisherError(
                "TIKTOK_PUBLISH_MODE must be either 'draft' or 'direct'"
            )

        return cls(access_token=token, mode=mode)  # type: ignore[arg-type]


@dataclass(frozen=True)
class TikTokPostRequest:
    video_path: Path
    caption: str
    privacy_level: str = "SELF_ONLY"
    disable_comment: bool = False
    disable_duet: bool = False
    disable_stitch: bool = False

    def validate(self) -> None:
        if not self.video_path.exists():
            raise TikTokPublisherError(f"Video does not exist: {self.video_path}")
        if self.video_path.suffix.lower() != ".mp4":
            raise TikTokPublisherError("TikTok publisher currently accepts MP4 only")
        if not self.caption.strip():
            raise TikTokPublisherError("Caption must not be empty")
        if len(self.caption) > 2200:
            raise TikTokPublisherError("Caption is longer than 2200 characters")


class TikTokPublisher:
    """Small TikTok Content Posting API client.

    The first production slice defaults to draft upload. Direct publishing is kept
    behind an explicit mode because public Direct Post requires the TikTok app to
    have the relevant Content Posting API permission/audit state.
    """

    def __init__(
        self,
        config: TikTokPublisherConfig,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config
        self.client = client or httpx.Client(timeout=config.timeout_seconds)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def query_creator_info(self) -> dict[str, Any]:
        response = self.client.post(
            f"{self.config.api_base}/post/publish/creator_info/query/",
            headers=self.headers,
            json={},
        )
        return self._json_or_raise(response)

    def initialize(self, request: TikTokPostRequest) -> dict[str, Any]:
        request.validate()
        size = request.video_path.stat().st_size

        if self.config.mode == "draft":
            endpoint = "/post/publish/inbox/video/init/"
            payload: dict[str, Any] = {
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": size,
                    "chunk_size": size,
                    "total_chunk_count": 1,
                }
            }
        else:
            endpoint = "/post/publish/video/init/"
            payload = {
                "post_info": {
                    "title": request.caption,
                    "privacy_level": request.privacy_level,
                    "disable_duet": request.disable_duet,
                    "disable_comment": request.disable_comment,
                    "disable_stitch": request.disable_stitch,
                    "video_cover_timestamp_ms": 1000,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": size,
                    "chunk_size": size,
                    "total_chunk_count": 1,
                },
            }

        response = self.client.post(
            f"{self.config.api_base}{endpoint}",
            headers=self.headers,
            json=payload,
        )
        return self._json_or_raise(response)

    def upload_video(self, upload_url: str, video_path: Path) -> None:
        size = video_path.stat().st_size
        with video_path.open("rb") as handle:
            response = self.client.put(
                upload_url,
                headers={
                    "Content-Range": f"bytes 0-{size - 1}/{size}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(size),
                },
                content=handle.read(),
            )
        if response.status_code not in {200, 201, 204}:
            raise TikTokPublisherError(
                f"TikTok video upload failed ({response.status_code}): {response.text[:500]}"
            )

    def get_publish_status(self, publish_id: str) -> dict[str, Any]:
        response = self.client.post(
            f"{self.config.api_base}/post/publish/status/fetch/",
            headers=self.headers,
            json={"publish_id": publish_id},
        )
        return self._json_or_raise(response)

    def publish(self, request: TikTokPostRequest) -> dict[str, Any]:
        """Initialize and upload one MP4, returning TikTok's publish identifier.

        In draft mode, this uploads the asset to TikTok's inbox/draft flow. In
        direct mode, TikTok handles the initialized Direct Post request according
        to the connected app's permissions and account settings.
        """
        init_result = self.initialize(request)
        data = init_result.get("data") or {}
        upload_url = data.get("upload_url")
        publish_id = data.get("publish_id")
        if not upload_url or not publish_id:
            raise TikTokPublisherError(
                "TikTok init response did not include upload_url and publish_id"
            )

        self.upload_video(upload_url, request.video_path)
        return {
            "mode": self.config.mode,
            "publish_id": publish_id,
            "status": "uploaded",
        }

    @staticmethod
    def _json_or_raise(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise TikTokPublisherError(
                f"TikTok API returned non-JSON response ({response.status_code})"
            ) from exc

        error = payload.get("error") or {}
        error_code = error.get("code")
        if response.is_error or (error_code and error_code != "ok"):
            message = error.get("message") or response.text[:500]
            raise TikTokPublisherError(
                f"TikTok API request failed ({response.status_code}, {error_code}): {message}"
            )
        return payload
