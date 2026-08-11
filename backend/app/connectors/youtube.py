import math
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import median

import httpx
from pydantic import BaseModel, Field

from app.connectors.base import ConnectorStatus

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeConfigurationError(RuntimeError):
    pass


class YouTubeAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class YouTubeConfig:
    api_key: str
    search_url: str = YOUTUBE_SEARCH_URL
    videos_url: str = YOUTUBE_VIDEOS_URL


class YouTubeMarketQuery(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    max_results: int = Field(default=15, ge=5, le=25)
    region_code: str | None = Field(default=None, min_length=2, max_length=2)
    relevance_language: str | None = Field(default=None, min_length=2, max_length=10)


class YouTubeMarketSignal(BaseModel):
    query: str
    sample_size: int
    median_views: int
    max_views: int
    recent_videos_90d: int
    high_view_videos: int
    established_videos: int
    interest_score: float = Field(ge=0, le=100)
    competition_score: float = Field(ge=0, le=100)
    evidence: list[str] = Field(default_factory=list)


def status() -> ConnectorStatus:
    configured = bool(os.getenv("YOUTUBE_API_KEY"))
    return ConnectorStatus(
        name="youtube",
        configured=configured,
        note=(
            "Live YouTube market research is ready. Set YOUTUBE_API_KEY."
            if not configured
            else "Live YouTube market research is configured."
        ),
    )


def config_from_env() -> YouTubeConfig:
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise YouTubeConfigurationError(
            "YouTube connector is not configured. Set YOUTUBE_API_KEY on the backend."
        )
    return YouTubeConfig(
        api_key=api_key,
        search_url=os.getenv("YOUTUBE_SEARCH_URL", YOUTUBE_SEARCH_URL).strip(),
        videos_url=os.getenv("YOUTUBE_VIDEOS_URL", YOUTUBE_VIDEOS_URL).strip(),
    )


def research_market(
    query: YouTubeMarketQuery,
    *,
    config: YouTubeConfig | None = None,
    client: httpx.Client | None = None,
    now: datetime | None = None,
) -> YouTubeMarketSignal:
    resolved = config or config_from_env()
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20.0)
    try:
        search_payload = _get_json(
            http_client,
            resolved.search_url,
            params=_search_params(query, resolved.api_key),
        )
        items = search_payload.get("items")
        if not isinstance(items, list):
            items = []

        video_ids: list[str] = []
        published_at: dict[str, datetime] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            identity = item.get("id")
            snippet = item.get("snippet")
            if not isinstance(identity, dict):
                continue
            video_id = str(identity.get("videoId") or "").strip()
            if not video_id:
                continue
            video_ids.append(video_id)
            if isinstance(snippet, dict):
                parsed_date = _parse_datetime(snippet.get("publishedAt"))
                if parsed_date is not None:
                    published_at[video_id] = parsed_date

        if not video_ids:
            return YouTubeMarketSignal(
                query=query.query,
                sample_size=0,
                median_views=0,
                max_views=0,
                recent_videos_90d=0,
                high_view_videos=0,
                established_videos=0,
                interest_score=0.0,
                competition_score=0.0,
                evidence=["No YouTube videos were returned for this query."],
            )

        videos_payload = _get_json(
            http_client,
            resolved.videos_url,
            params={
                "part": "statistics",
                "id": ",".join(video_ids),
                "key": resolved.api_key,
            },
        )
    finally:
        if owns_client:
            http_client.close()

    video_items = videos_payload.get("items")
    if not isinstance(video_items, list):
        video_items = []

    views: list[int] = []
    for item in video_items:
        if not isinstance(item, dict):
            continue
        stats = item.get("statistics")
        if not isinstance(stats, dict):
            continue
        views.append(_safe_int(stats.get("viewCount")))

    sample_size = len(video_ids)
    view_values = views or [0]
    median_views = int(median(view_values))
    max_views = max(view_values)
    reference_time = now or datetime.now(UTC)
    recent_cutoff = reference_time - timedelta(days=90)
    established_cutoff = reference_time - timedelta(days=365)
    recent = sum(1 for value in published_at.values() if value >= recent_cutoff)
    established = sum(1 for value in published_at.values() if value <= established_cutoff)
    high_view = sum(1 for value in views if value >= 100_000)

    recent_ratio = recent / sample_size if sample_size else 0.0
    established_ratio = established / sample_size if sample_size else 0.0
    high_view_ratio = high_view / len(views) if views else 0.0

    interest_score = _clamp(
        _log_score(median_views, ceiling=1_000_000) * 75.0 + recent_ratio * 25.0
    )
    competition_score = _clamp(
        high_view_ratio * 45.0
        + established_ratio * 20.0
        + _log_score(max_views, ceiling=10_000_000) * 35.0
    )

    evidence = [
        f"Median views across sampled videos: {median_views:,}",
        f"Recent videos in last 90 days: {recent}/{sample_size}",
        f"Videos above 100k views: {high_view}/{len(views)}",
    ]
    return YouTubeMarketSignal(
        query=query.query,
        sample_size=sample_size,
        median_views=median_views,
        max_views=max_views,
        recent_videos_90d=recent,
        high_view_videos=high_view,
        established_videos=established,
        interest_score=round(interest_score, 2),
        competition_score=round(competition_score, 2),
        evidence=evidence,
    )


def _search_params(query: YouTubeMarketQuery, api_key: str) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "part": "snippet",
        "q": query.query,
        "type": "video",
        "order": "relevance",
        "maxResults": query.max_results,
        "safeSearch": "moderate",
        "key": api_key,
    }
    if query.region_code:
        params["regionCode"] = query.region_code.upper()
    if query.relevance_language:
        params["relevanceLanguage"] = query.relevance_language
    return params


def _get_json(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, str | int],
) -> dict[str, object]:
    try:
        response = client.get(url, params=params, headers={"Accept": "application/json"})
    except httpx.RequestError as exc:
        raise YouTubeAPIError("Could not reach the YouTube Data API.") from exc

    if response.status_code in {401, 403}:
        raise YouTubeAPIError("YouTube rejected the API key or the project lacks API access.")
    if response.status_code == 429:
        raise YouTubeAPIError("YouTube quota or rate limit was reached.")
    if response.status_code >= 400:
        raise YouTubeAPIError(f"YouTube Data API returned HTTP {response.status_code}.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise YouTubeAPIError("YouTube returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise YouTubeAPIError("YouTube returned an unexpected response shape.")
    return payload


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _safe_int(value: object) -> int:
    try:
        return max(0, int(str(value)))
    except (TypeError, ValueError):
        return 0


def _log_score(value: int, *, ceiling: int) -> float:
    if value <= 0:
        return 0.0
    return min(1.0, math.log10(value + 1) / math.log10(ceiling + 1))


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))
