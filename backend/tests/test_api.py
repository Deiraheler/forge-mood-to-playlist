"""
API integration tests for POST /api/generate and GET /api/health.

All tests are self-contained — no live OpenAI key or Redis required.
- OpenAI is mocked via ``ai_service.generate_playlist`` patch.
- Redis is bypassed with an in-memory cache store via dependency override +
  cache helper patches.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fake playlist data
# ---------------------------------------------------------------------------

FAKE_PLAYLIST = {
    "playlist_name": "Midnight Stillness",
    "description": "Soft, introspective tracks for the quiet hours.",
    "tracks": [
        {"title": "Holocene", "artist": "Bon Iver", "vibe": "Wistful and expansive."},
        {"title": "Motion Picture Soundtrack", "artist": "Radiohead", "vibe": "Haunting lullaby."},
        {"title": "Breathe (2 AM)", "artist": "Anna Nalick", "vibe": "Honest 2 AM confessions."},
        {"title": "Let Her Go", "artist": "Passenger", "vibe": "Aching melancholy."},
        {"title": "Skinny Love", "artist": "Bon Iver", "vibe": "Raw, stripped-back grief."},
        {"title": "The Night Will Always Win", "artist": "Manchester Orchestra", "vibe": "Dark beauty."},
        {"title": "Youth", "artist": "Daughter", "vibe": "Tender resignation."},
        {"title": "I'll Be Your Mirror", "artist": "The Velvet Underground", "vibe": "Gentle reassurance."},
    ],
}

# ---------------------------------------------------------------------------
# In-memory cache store shared across helpers
# ---------------------------------------------------------------------------

_cache_store: dict[str, str] = {}


async def _fake_get_cached(redis, mood: str):
    from models import PlaylistResponse
    key = mood.strip().lower()
    if key in _cache_store:
        return PlaylistResponse.model_validate_json(_cache_store[key])
    return None


async def _fake_set_cached(redis, mood: str, playlist):
    key = mood.strip().lower()
    _cache_store[key] = playlist.model_dump_json()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache():
    """Reset in-memory cache before and after each test."""
    _cache_store.clear()
    yield
    _cache_store.clear()


@pytest.fixture()
def client():
    """
    Synchronous TestClient with:
    - ``ai_service.generate_playlist`` mocked to return FAKE_PLAYLIST.
    - Cache helpers patched to use ``_cache_store`` (in-memory dict).
    - ``get_redis`` dependency overridden to return ``None``.
    """

    async def _fake_generate(mood: str):
        from models import PlaylistResponse
        data = {**FAKE_PLAYLIST, "mood": mood, "cached": False}
        return PlaylistResponse.model_validate(data)

    with (
        patch("main.get_cached_playlist", side_effect=_fake_get_cached),
        patch("main.set_cached_playlist", side_effect=_fake_set_cached),
        patch("main.ai_service.generate_playlist", side_effect=_fake_generate),
    ):
        from main import app
        from cache import get_redis

        async def _override_redis():
            yield None

        app.dependency_overrides[get_redis] = _override_redis

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self, client: TestClient):
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_health_body(self, client: TestClient):
        r = client.get("/api/health")
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/generate — happy path
# ---------------------------------------------------------------------------

class TestGenerateHappyPath:
    def test_valid_mood_returns_200(self, client: TestClient):
        r = client.post("/api/generate", json={"mood": "3am can't sleep"})
        assert r.status_code == 200

    def test_response_matches_playlist_response_schema(self, client: TestClient):
        """Response body must be parseable as a PlaylistResponse."""
        from models import PlaylistResponse

        r = client.post("/api/generate", json={"mood": "driving through rain"})
        assert r.status_code == 200
        # Raises ValidationError if schema doesn't match
        playlist = PlaylistResponse.model_validate(r.json())
        assert playlist.mood == "driving through rain"
        assert len(playlist.tracks) > 0

    def test_response_has_all_required_fields(self, client: TestClient):
        r = client.post("/api/generate", json={"mood": "sunday morning coffee"})
        assert r.status_code == 200
        body = r.json()
        for field in ("mood", "playlist_name", "description", "tracks", "cached"):
            assert field in body, f"Missing required field: {field}"

    def test_tracks_have_title_artist_vibe(self, client: TestClient):
        r = client.post("/api/generate", json={"mood": "late night studying"})
        assert r.status_code == 200
        for i, track in enumerate(r.json()["tracks"]):
            for key in ("title", "artist", "vibe"):
                assert key in track, f"Track {i} missing '{key}'"

    def test_mood_echoed_in_response(self, client: TestClient):
        mood = "feeling nostalgic"
        r = client.post("/api/generate", json={"mood": mood})
        assert r.status_code == 200
        assert r.json()["mood"] == mood

    def test_xcache_miss_header_on_first_request(self, client: TestClient):
        r = client.post("/api/generate", json={"mood": "morning run"})
        assert r.status_code == 200
        assert r.headers.get("x-cache", "").upper() == "MISS"

    def test_cached_false_on_first_request(self, client: TestClient):
        r = client.post("/api/generate", json={"mood": "rainy sunday"})
        assert r.status_code == 200
        assert r.json()["cached"] is False

    def test_exactly_200_char_mood_is_accepted(self, client: TestClient):
        mood = "a" * 200
        r = client.post("/api/generate", json={"mood": mood})
        assert r.status_code == 200

    def test_single_char_mood_is_accepted(self, client: TestClient):
        r = client.post("/api/generate", json={"mood": "x"})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/generate — validation errors (422)
# ---------------------------------------------------------------------------

class TestGenerateValidation:
    def test_empty_mood_returns_422(self, client: TestClient):
        r = client.post("/api/generate", json={"mood": ""})
        assert r.status_code == 422

    def test_empty_mood_has_detail(self, client: TestClient):
        r = client.post("/api/generate", json={"mood": ""})
        assert "detail" in r.json()

    def test_missing_mood_field_returns_422(self, client: TestClient):
        r = client.post("/api/generate", json={})
        assert r.status_code == 422

    def test_mood_over_200_chars_returns_422(self, client: TestClient):
        r = client.post("/api/generate", json={"mood": "x" * 201})
        assert r.status_code == 422

    def test_mood_over_200_chars_has_detail(self, client: TestClient):
        r = client.post("/api/generate", json={"mood": "x" * 201})
        assert "detail" in r.json()

    def test_201_chars_is_rejected(self, client: TestClient):
        """Boundary: 200 chars accepted, 201 rejected."""
        r = client.post("/api/generate", json={"mood": "y" * 201})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Cache behaviour
# ---------------------------------------------------------------------------

class TestCacheBehaviour:
    def test_second_request_returns_xcache_hit(self, client: TestClient):
        mood = "walking in the fog"
        client.post("/api/generate", json={"mood": mood})  # prime cache
        r2 = client.post("/api/generate", json={"mood": mood})
        assert r2.status_code == 200
        assert r2.headers.get("x-cache", "").upper() == "HIT"

    def test_cached_true_on_cache_hit(self, client: TestClient):
        mood = "coffee shop jazz"
        client.post("/api/generate", json={"mood": mood})  # prime cache
        r2 = client.post("/api/generate", json={"mood": mood})
        assert r2.status_code == 200
        assert r2.json()["cached"] is True

    def test_cache_hit_returns_same_data_as_miss(self, client: TestClient):
        mood = "summer evening breeze"
        r1 = client.post("/api/generate", json={"mood": mood})
        r2 = client.post("/api/generate", json={"mood": mood})
        assert r1.status_code == r2.status_code == 200
        b1, b2 = r1.json(), r2.json()
        assert b1["playlist_name"] == b2["playlist_name"]
        assert b1["description"] == b2["description"]
        assert len(b1["tracks"]) == len(b2["tracks"])
        for t1, t2 in zip(b1["tracks"], b2["tracks"]):
            assert t1["title"] == t2["title"]
            assert t1["artist"] == t2["artist"]

    def test_different_moods_are_cached_separately(self, client: TestClient):
        moods = ["3am can't sleep", "driving through rain", "sunday morning coffee"]
        for mood in moods:
            r = client.post("/api/generate", json={"mood": mood})
            assert r.status_code == 200
            assert r.headers.get("x-cache", "").upper() == "MISS", (
                f"Expected MISS for '{mood}', got {r.headers.get('x-cache')}"
            )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_ai_runtime_error_returns_500(self, client: TestClient):
        with patch("ai_service.generate_playlist", side_effect=RuntimeError("OpenAI timeout")):
            r = client.post("/api/generate", json={"mood": "trigger failure"})
        assert r.status_code == 500

    def test_ai_value_error_returns_500(self, client: TestClient):
        with patch("ai_service.generate_playlist", side_effect=ValueError("bad JSON from AI")):
            r = client.post("/api/generate", json={"mood": "trigger failure"})
        assert r.status_code == 500

    def test_500_response_has_detail(self, client: TestClient):
        with patch("ai_service.generate_playlist", side_effect=RuntimeError("boom")):
            r = client.post("/api/generate", json={"mood": "fail please"})
        assert "detail" in r.json()

    def test_wrong_content_type_returns_422(self, client: TestClient):
        r = client.post(
            "/api/generate",
            content="not json at all",
            headers={"Content-Type": "text/plain"},
        )
        assert r.status_code == 422
