from datetime import UTC, datetime

import httpx
import pytest

from app.connectors.youtube import (
    YouTubeAPIError,
    YouTubeConfig,
    YouTubeMarketQuery,
    research_market,
)

SEARCH_JSON = {
    "items": [
        {
            "id": {"videoId": "a"},
            "snippet": {"publishedAt": "2026-08-01T12:00:00Z"},
        },
        {
            "id": {"videoId": "b"},
            "snippet": {"publishedAt": "2026-07-15T12:00:00Z"},
        },
        {
            "id": {"videoId": "c"},
            "snippet": {"publishedAt": "2024-01-01T12:00:00Z"},
        },
    ]
}

VIDEOS_JSON = {
    "items": [
        {"id": "a", "statistics": {"viewCount": "250000"}},
        {"id": "b", "statistics": {"viewCount": "80000"}},
        {"id": "c", "statistics": {"viewCount": "1200000"}},
    ]
}


def test_research_market_builds_interest_and_competition_signal() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/search"):
            assert request.url.params["q"] == "ElevenLabs AI voice"
            assert request.url.params["type"] == "video"
            assert request.url.params["safeSearch"] == "moderate"
            return httpx.Response(200, json=SEARCH_JSON)
        assert request.url.params["id"] == "a,b,c"
        return httpx.Response(200, json=VIDEOS_JSON)

    config = YouTubeConfig(
        api_key="safe-test-key",
        search_url="https://youtube.test/search",
        videos_url="https://youtube.test/videos",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = research_market(
            YouTubeMarketQuery(query="ElevenLabs AI voice", max_results=15),
            config=config,
            client=client,
            now=datetime(2026, 8, 11, tzinfo=UTC),
        )

    assert calls == ["/search", "/videos"]
    assert result.sample_size == 3
    assert result.median_views == 250000
    assert result.max_views == 1200000
    assert result.recent_videos_90d == 2
    assert result.high_view_videos == 2
    assert result.established_videos == 1
    assert 0 < result.interest_score <= 100
    assert 0 < result.competition_score <= 100


def test_youtube_auth_failure_is_safe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, request=request)

    config = YouTubeConfig(
        api_key="do-not-leak",
        search_url="https://youtube.test/search",
        videos_url="https://youtube.test/videos",
    )
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(YouTubeAPIError, match="rejected the API key"),
    ):
        research_market(
            YouTubeMarketQuery(query="AI software"),
            config=config,
            client=client,
        )
