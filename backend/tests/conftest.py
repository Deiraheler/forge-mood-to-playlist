"""
Pytest configuration and shared fixtures for the backend test suite.

Fixtures provided
-----------------
client
    Synchronous ``TestClient`` wrapping the FastAPI app.  The ``get_redis``
    dependency is overridden so no real Redis connection is needed.

mock_redis
    An ``AsyncMock`` that mimics the ``redis.asyncio.Redis`` interface used by
    ``cache.py``.  By default ``get`` returns ``None`` (cache miss) and ``set``
    / ``ping`` succeed silently.

mock_openai_response
    A dictionary matching the JSON structure the OpenAI API returns, used to
    patch ``ai_service._call_openai``.

sample_playlist
    A fully-constructed ``PlaylistResponse`` instance ready for assertion use.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Path adjustment — tests run from backend/ so bare module imports work
# ---------------------------------------------------------------------------
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # adds backend/ to path

from main import app  # noqa: E402  (must come after sys.path tweak)
from models import PlaylistResponse, Track  # noqa: E402
import cache  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_playlist_response(cached: bool = False) -> PlaylistResponse:
    """Return a fully-populated PlaylistResponse suitable for test assertions."""
    return PlaylistResponse(
        mood="3am can't sleep",
        playlist_name="Insomnia Echoes",
        description=(
            "Quiet, introspective tracks that keep you company in the small hours. "
            "Melancholy without despair, warm without false cheer."
        ),
        tracks=[
            Track(
                title="Motion Picture Soundtrack",
                artist="Radiohead",
                vibe="Hushed and haunting — the perfect 3am companion.",
            ),
            Track(
                title="Blue Light",
                artist="Mazzy Star",
                vibe="Dreamy and slow, like drifting between sleep and waking.",
            ),
            Track(
                title="Breathe (In the Air)",
                artist="Pink Floyd",
                vibe="An expansive opener that mirrors the stillness of night.",
            ),
            Track(
                title="Georgia",
                artist="Blink-182",
                vibe="Tender and raw — honest late-night emotion.",
            ),
            Track(
                title="Holocene",
                artist="Bon Iver",
                vibe="Expansive and melancholic, perfectly suited to dark skies.",
            ),
            Track(
                title="The Night Will Always Win",
                artist="Manchester Orchestra",
                vibe="Quietly powerful, capturing sleepless surrender.",
            ),
            Track(
                title="Such Great Heights",
                artist="Iron & Wine",
                vibe="The acoustic cover turns an indie-pop hit into a lullaby.",
            ),
            Track(
                title="Lua",
                artist="Bright Eyes",
                vibe="Confessional and intimate — words for a sleepless mind.",
            ),
            Track(
                title="Night Owl",
                artist="Galimatias",
                vibe="Gentle electronic warmth for the wide-awake hours.",
            ),
            Track(
                title="Skinny Love",
                artist="Bon Iver",
                vibe="Raw and aching — an anthem for quiet suffering.",
            ),
        ],
        cached=cached,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_playlist() -> PlaylistResponse:
    """A valid PlaylistResponse instance for use in assertions."""
    return _make_playlist_response()


@pytest.fixture()
def sample_playlist_json() -> str:
    """JSON string of the AI response structure (no 'mood' / 'cached' keys)."""
    playlist = _make_playlist_response()
    data = {
        "playlist_name": playlist.playlist_name,
        "description": playlist.description,
        "tracks": [t.model_dump() for t in playlist.tracks],
    }
    return json.dumps(data)


@pytest.fixture()
def mock_redis() -> AsyncMock:
    """
    AsyncMock that mimics ``redis.asyncio.Redis``.

    Default behaviour:
    - ``ping()``   → returns ``True``
    - ``get(key)`` → returns ``None``  (cache miss)
    - ``set(...)`` → returns ``True``
    """
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None   # cache miss by default
    redis_mock.set.return_value = True
    return redis_mock


@pytest.fixture()
def client(mock_redis: AsyncMock) -> TestClient:
    """
    Synchronous FastAPI TestClient with the ``get_redis`` dependency overridden
    to return ``mock_redis`` instead of a real Redis connection.
    """

    async def _override_get_redis() -> AsyncGenerator:
        yield mock_redis

    app.dependency_overrides[cache.get_redis] = _override_get_redis

    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client

    # Clean up overrides after each test
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_openai_response(sample_playlist_json: str) -> MagicMock:
    """
    Patch ``ai_service._call_openai`` to return ``sample_playlist_json``
    without hitting the real OpenAI API.

    Usage::

        def test_something(client, mock_openai_response):
            resp = client.post("/api/generate", json={"mood": "3am can't sleep"})
            assert resp.status_code == 200
    """
    with patch("ai_service._call_openai", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = sample_playlist_json
        yield mock_fn
