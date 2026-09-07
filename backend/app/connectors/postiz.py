import mimetypes
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.connectors.base import ConnectorStatus

POSTIZ_API_BASE_URL = "https://api.postiz.com/public/v1"
MAYA_SUPPORTED_PROVIDERS = {"tiktok", "youtube", "instagram", "instagram-standalone"}


class PostizConfigurationError(RuntimeError):
    pass


class PostizAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class PostizConfig:
    api_key: str
    base_url: str = POSTIZ_API_BASE_URL


class PostizCustomer(BaseModel):
    id: str
    name: str | None = None


class PostizIntegration(BaseModel):
    id: str
    name: str
    identifier: str
    picture: str | None = None
    disabled: bool = False
    profile: str | None = None
    customer: PostizCustomer | None = None


class PostizMedia(BaseModel):
    id: str
    path: str
    name: str | None = None


class PostizCreatedPost(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    post_id: str = Field(alias="postId")
    integration: str


class PostizChannelPost(BaseModel):
    integration_id: str = Field(min_length=1)
    content: str = Field(default="", max_length=20000)
    settings: dict[str, object]
    media: list[PostizMedia] = Field(default_factory=list)


PostizPublishMode = Literal["draft", "schedule", "now"]


def status() -> ConnectorStatus:
    configured = bool(os.getenv("POSTIZ_API_KEY", "").strip())
    return ConnectorStatus(
        name="postiz",
        configured=configured,
        note=(
            "Postiz social publishing is configured."
            if configured
            else "Set POSTIZ_API_KEY to enable the Maya social publishing buffer."
        ),
    )


def config_from_env() -> PostizConfig:
    api_key = os.getenv("POSTIZ_API_KEY", "").strip()
    if not api_key:
        raise PostizConfigurationError(
            "Postiz is not configured. Set POSTIZ_API_KEY on the backend."
        )
    base_url = os.getenv("POSTIZ_API_BASE_URL", POSTIZ_API_BASE_URL).strip().rstrip("/")
    if not base_url:
        base_url = POSTIZ_API_BASE_URL
    return PostizConfig(api_key=api_key, base_url=base_url)


def list_integrations(
    *,
    group: str | None = None,
    config: PostizConfig | None = None,
    client: httpx.Client | None = None,
) -> list[PostizIntegration]:
    resolved = config or config_from_env()
    payload = _request_json(
        "GET",
        f"{resolved.base_url}/integrations",
        config=resolved,
        client=client,
        params={"group": group} if group else None,
    )
    if not isinstance(payload, list):
        raise PostizAPIError("Postiz returned an unexpected integrations response.")
    try:
        return [PostizIntegration.model_validate(item) for item in payload]
    except (TypeError, ValueError) as exc:
        raise PostizAPIError("Postiz returned invalid integration data.") from exc


def upload_from_url(
    url: str,
    *,
    config: PostizConfig | None = None,
    client: httpx.Client | None = None,
) -> PostizMedia:
    if not url.lower().startswith("https://"):
        raise ValueError("Postiz remote media must use a publicly reachable HTTPS URL.")
    resolved = config or config_from_env()
    payload = _request_json(
        "POST",
        f"{resolved.base_url}/upload-from-url",
        config=resolved,
        client=client,
        json={"url": url},
    )
    if not isinstance(payload, dict):
        raise PostizAPIError("Postiz returned an unexpected upload response.")
    try:
        return PostizMedia.model_validate(payload)
    except ValueError as exc:
        raise PostizAPIError("Postiz returned invalid upload metadata.") from exc


def upload_file(
    file_path: str | Path,
    *,
    config: PostizConfig | None = None,
    client: httpx.Client | None = None,
) -> PostizMedia:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Media file does not exist: {path}")

    resolved = config or config_from_env()
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    owns_client = client is None
    http_client = client or httpx.Client(timeout=120.0)
    try:
        with path.open("rb") as handle:
            try:
                response = http_client.post(
                    f"{resolved.base_url}/upload",
                    headers={"Authorization": resolved.api_key},
                    files={"file": (path.name, handle, mime_type)},
                )
            except httpx.RequestError as exc:
                raise PostizAPIError("Could not reach Postiz while uploading media.") from exc
        payload = _decode_response(response)
    finally:
        if owns_client:
            http_client.close()

    if not isinstance(payload, dict):
        raise PostizAPIError("Postiz returned an unexpected upload response.")
    try:
        return PostizMedia.model_validate(payload)
    except ValueError as exc:
        raise PostizAPIError("Postiz returned invalid upload metadata.") from exc


def create_posts(
    posts: list[PostizChannelPost],
    *,
    mode: PostizPublishMode = "draft",
    scheduled_at: datetime | None = None,
    short_link: bool = False,
    tags: list[dict[str, object]] | None = None,
    config: PostizConfig | None = None,
    client: httpx.Client | None = None,
) -> list[PostizCreatedPost]:
    if not posts:
        raise ValueError("At least one social channel post is required.")
    if mode == "schedule" and scheduled_at is None:
        raise ValueError("scheduled_at is required when mode='schedule'.")
    if scheduled_at is not None and scheduled_at.tzinfo is None:
        raise ValueError("scheduled_at must include a timezone.")

    resolved = config or config_from_env()
    publish_time = scheduled_at or datetime.now(UTC)
    publish_time = publish_time.astimezone(UTC)
    date_value = publish_time.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    payload = {
        "type": mode,
        "date": date_value,
        "shortLink": short_link,
        "tags": tags or [],
        "posts": [
            {
                "integration": {"id": item.integration_id},
                "value": [
                    {
                        "content": item.content,
                        "image": [media.model_dump(include={"id", "path"}) for media in item.media],
                    }
                ],
                "settings": item.settings,
            }
            for item in posts
        ],
    }
    response_payload = _request_json(
        "POST",
        f"{resolved.base_url}/posts",
        config=resolved,
        client=client,
        json=payload,
    )
    if not isinstance(response_payload, list):
        raise PostizAPIError("Postiz returned an unexpected create-post response.")
    try:
        return [PostizCreatedPost.model_validate(item) for item in response_payload]
    except (TypeError, ValueError) as exc:
        raise PostizAPIError("Postiz returned invalid created-post data.") from exc


def build_maya_channel_post(
    integration: PostizIntegration,
    *,
    content: str,
    title: str,
    media: list[PostizMedia] | None = None,
    branded_content: bool = False,
    tiktok_upload_only: bool = False,
    youtube_visibility: Literal["public", "unlisted", "private"] = "public",
) -> PostizChannelPost:
    provider = integration.identifier
    if provider not in MAYA_SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Maya's guarded publisher currently supports {sorted(MAYA_SUPPORTED_PROVIDERS)}; "
            f"got {provider!r}."
        )
    if integration.disabled:
        raise ValueError(f"Postiz integration {integration.id} is disabled.")

    guarded_content = ensure_maya_ai_disclosure(content)
    settings = maya_provider_settings(
        provider,
        title=title,
        branded_content=branded_content,
        tiktok_upload_only=tiktok_upload_only,
        youtube_visibility=youtube_visibility,
    )
    return PostizChannelPost(
        integration_id=integration.id,
        content=guarded_content,
        settings=settings,
        media=media or [],
    )


def maya_provider_settings(
    provider: str,
    *,
    title: str,
    branded_content: bool = False,
    tiktok_upload_only: bool = False,
    youtube_visibility: Literal["public", "unlisted", "private"] = "public",
) -> dict[str, object]:
    if provider == "tiktok":
        return {
            "__type": "tiktok",
            "title": title[:90],
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "duet": False,
            "stitch": False,
            "comment": True,
            "autoAddMusic": "no",
            "brand_content_toggle": branded_content,
            "brand_organic_toggle": branded_content,
            "video_made_with_ai": True,
            "content_posting_method": "UPLOAD" if tiktok_upload_only else "DIRECT_POST",
        }
    if provider == "youtube":
        cleaned_title = title.strip()
        if len(cleaned_title) < 2:
            raise ValueError("YouTube title must contain at least 2 characters.")
        return {
            "__type": "youtube",
            "title": cleaned_title[:100],
            "type": youtube_visibility,
            "selfDeclaredMadeForKids": "no",
            "tags": [],
        }
    if provider in {"instagram", "instagram-standalone"}:
        return {
            "__type": provider,
            "post_type": "post",
            "is_trial_reel": False,
            "collaborators": [],
        }
    raise ValueError(f"Unsupported Maya provider: {provider}")


def ensure_maya_ai_disclosure(content: str) -> str:
    disclosure = "Virtual AI creator • AI-generated content"
    lowered = content.lower()
    if "virtual ai creator" in lowered or "ai-generated content" in lowered:
        return content
    if not content.strip():
        return disclosure
    return f"{content.rstrip()}\n\n{disclosure}"


def _request_json(
    method: str,
    url: str,
    *,
    config: PostizConfig,
    client: httpx.Client | None,
    params: dict[str, object] | None = None,
    json: dict[str, object] | None = None,
) -> object:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=30.0)
    try:
        try:
            response = http_client.request(
                method,
                url,
                headers={
                    "Authorization": config.api_key,
                    "Accept": "application/json",
                },
                params=params,
                json=json,
            )
        except httpx.RequestError as exc:
            raise PostizAPIError("Could not reach the Postiz API.") from exc
        return _decode_response(response)
    finally:
        if owns_client:
            http_client.close()


def _decode_response(response: httpx.Response) -> object:
    if response.status_code == 401:
        raise PostizAPIError("Postiz rejected the API key.")
    if response.status_code == 403:
        raise PostizAPIError("Postiz denied access to this organization or resource.")
    if response.status_code == 404:
        raise PostizAPIError("Postiz could not find the requested resource.")
    if response.status_code == 429:
        raise PostizAPIError("Postiz create-post rate limit was reached; retry later.")
    if response.status_code >= 500:
        raise PostizAPIError(f"Postiz returned server error HTTP {response.status_code}.")
    if response.status_code >= 400:
        detail = _safe_error_detail(response)
        suffix = f": {detail}" if detail else ""
        raise PostizAPIError(f"Postiz returned HTTP {response.status_code}{suffix}")
    try:
        return response.json()
    except ValueError as exc:
        raise PostizAPIError("Postiz returned invalid JSON.") from exc


def _safe_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    for key in ("message", "error", "detail"):
        value = payload.get(key)
        if value:
            return str(value)[:300]
    return ""
