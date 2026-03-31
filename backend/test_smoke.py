"""
Smoke tests for POST /api/generate and GET /api/health.

Tests are fully self-contained — no live OpenAI key or Redis needed.
OpenAI is mocked at the httpx transport level; Redis is bypassed via
dependency-override so we can also test real cache-hit behaviour using
an in-memory dict.
"""

import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import Response as HttpxResponse

# ---------------------------------------------------------------------------
# Patch OpenAI *before* importing the app so the module-level client never
# tries to authenticate.
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


def _make_openai_response(mood: str, payload: dict | None = None) -> MagicMock:
    """Return a mock ChatCompletion object with a JSON content string."""
    content = json.dumps(payload or FAKE_PLAYLIST)
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


# ---------------------------------------------------------------------------
# In-memory cache store for testing cache-hit behaviour
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
    """Reset in-memory cache before each test."""
    _cache_store.clear()
    yield
    _cache_store.clear()


@pytest.fixture()
def client():
    """
    TestClient with:
    - OpenAI async client mocked to return FAKE_PLAYLIST JSON
    - Redis dependency overridden to None (cache helpers patched separately)
    """
    with patch("ai_service.settings") as mock_settings, \
         patch("cache.get_cached_playlist", side_effect=_fake_get_cached), \
         patch("cache.set_cached_playlist", side_effect=_fake_set_cached):

        mock_settings.OPENAI_API_KEY = "sk-test-key"

        async def _fake_generate(mood: str):
            from models import PlaylistResponse
            data = {**FAKE_PLAYLIST, "mood": mood, "cached": False}
            return PlaylistResponse.model_validate(data)

        with patch("ai_service.generate_playlist", side_effect=_fake_generate):
            from main import app
            from cache import get_redis

            async def _override_redis():
                yield None  # no real Redis needed

            app.dependency_overrides[get_redis] = _override_redis

            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body == {"status": "ok"}, f"Unexpected body: {body}"
        print("✅ /api/health → 200 OK")


class TestGeneratePlaylist:
    def _assert_valid_playlist(self, body: dict, mood: str):
        assert "playlist_name" in body, "Missing playlist_name"
        assert "description" in body, "Missing description"
        assert "tracks" in body, "Missing tracks"
        assert isinstance(body["tracks"], list), "tracks must be a list"
        assert len(body["tracks"]) > 0, "tracks must be non-empty"
        assert body["mood"] == mood, f"mood echo mismatch: {body['mood']!r} != {mood!r}"
        for i, track in enumerate(body["tracks"]):
            assert "title" in track, f"Track {i} missing title"
            assert "artist" in track, f"Track {i} missing artist"
            assert "vibe" in track, f"Track {i} missing vibe"

    def test_3am_cant_sleep(self, client):
        mood = "3am can't sleep"
        r = client.post("/api/generate", json={"mood": mood})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        self._assert_valid_playlist(body, mood)
        assert r.headers.get("x-cache", "").upper() == "MISS"
        print(f"✅ mood='{mood}' → {body['playlist_name']!r} ({len(body['tracks'])} tracks), X-Cache: MISS")

    def test_driving_through_rain(self, client):
        mood = "driving through rain"
        r = client.post("/api/generate", json={"mood": mood})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        self._assert_valid_playlist(body, mood)
        assert r.headers.get("x-cache", "").upper() == "MISS"
        print(f"✅ mood='{mood}' → {body['playlist_name']!r} ({len(body['tracks'])} tracks), X-Cache: MISS")

    def test_sunday_morning_coffee(self, client):
        mood = "sunday morning coffee"
        r = client.post("/api/generate", json={"mood": mood})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        self._assert_valid_playlist(body, mood)
        assert r.headers.get("x-cache", "").upper() == "MISS"
        print(f"✅ mood='{mood}' → {body['playlist_name']!r} ({len(body['tracks'])} tracks), X-Cache: MISS")


class TestCacheBehavior:
    def test_cache_hit_on_repeat_request(self, client):
        mood = "sunday morning coffee"

        # First request — should be a cache MISS
        r1 = client.post("/api/generate", json={"mood": mood})
        assert r1.status_code == 200
        assert r1.headers.get("x-cache", "").upper() == "MISS"
        body1 = r1.json()
        assert body1["cached"] is False

        # Second identical request — should be a cache HIT
        r2 = client.post("/api/generate", json={"mood": mood})
        assert r2.status_code == 200
        assert r2.headers.get("x-cache", "").upper() == "HIT"
        body2 = r2.json()
        assert body2["cached"] is True

        # Content must be identical across both responses
        assert body1["playlist_name"] == body2["playlist_name"]
        assert len(body1["tracks"]) == len(body2["tracks"])
        print(f"✅ Cache hit verified: first=MISS, second=HIT for mood='{mood}'")

    def test_different_moods_have_separate_cache_entries(self, client):
        moods = ["3am can't sleep", "driving through rain", "sunday morning coffee"]
        for mood in moods:
            r = client.post("/api/generate", json={"mood": mood})
            assert r.status_code == 200
            assert r.headers.get("x-cache", "").upper() == "MISS", \
                f"Expected MISS for new mood '{mood}', got {r.headers.get('x-cache')}"
        print(f"✅ {len(moods)} different moods → {len(moods)} separate cache MISS entries")


class TestErrorHandling:
    def test_empty_mood_returns_422(self, client):
        r = client.post("/api/generate", json={"mood": ""})
        assert r.status_code == 422, f"Expected 422 for empty mood, got {r.status_code}"
        body = r.json()
        assert "detail" in body
        print(f"✅ Empty mood → 422 Unprocessable Entity: {body['detail']}")

    def test_missing_mood_field_returns_422(self, client):
        r = client.post("/api/generate", json={})
        assert r.status_code == 422, f"Expected 422 for missing mood, got {r.status_code}"
        print("✅ Missing mood field → 422 Unprocessable Entity")

    def test_too_long_mood_returns_422(self, client):
        too_long = "x" * 201
        r = client.post("/api/generate", json={"mood": too_long})
        assert r.status_code == 422, f"Expected 422 for 201-char mood, got {r.status_code}"
        body = r.json()
        assert "detail" in body
        print(f"✅ 201-char mood → 422: {body['detail']}")

    def test_exactly_200_chars_is_accepted(self, client):
        exactly_200 = "a" * 200
        r = client.post("/api/generate", json={"mood": exactly_200})
        assert r.status_code == 200, f"Expected 200 for 200-char mood, got {r.status_code}: {r.text}"
        print("✅ Exactly 200-char mood → 200 OK (boundary accepted)")

    def test_non_string_mood_returns_422(self, client):
        r = client.post("/api/generate", json={"mood": 12345})
        # Pydantic will coerce int to str, so this may succeed or fail depending on version
        # Either 200 (coerced) or 422 (rejected) is acceptable — just not 500
        assert r.status_code in (200, 422), \
            f"Expected 200 or 422 for numeric mood, got {r.status_code}"
        print(f"✅ Numeric mood → {r.status_code} (no 500 error)")

    def test_ai_failure_returns_500(self, client):
        """Override generate_playlist to raise RuntimeError and expect HTTP 500."""
        from unittest.mock import patch as _patch

        with _patch("ai_service.generate_playlist", side_effect=RuntimeError("OpenAI timeout")):
            r = client.post("/api/generate", json={"mood": "test failure"})
        assert r.status_code == 500, f"Expected 500 on AI failure, got {r.status_code}"
        body = r.json()
        assert "detail" in body
        print(f"✅ AI RuntimeError → 500: {body['detail']}")

    def test_wrong_content_type_returns_422(self, client):
        r = client.post(
            "/api/generate",
            content="not json at all",
            headers={"Content-Type": "text/plain"},
        )
        assert r.status_code == 422, f"Expected 422 for plain-text body, got {r.status_code}"
        print("✅ Wrong Content-Type → 422 Unprocessable Entity")


class TestResponseStructure:
    def test_response_has_all_required_fields(self, client):
        r = client.post("/api/generate", json={"mood": "feeling nostalgic"})
        assert r.status_code == 200
        body = r.json()
        required_top = {"mood", "playlist_name", "description", "tracks", "cached"}
        missing = required_top - set(body.keys())
        assert not missing, f"Response missing fields: {missing}"
        required_track = {"title", "artist", "vibe"}
        for i, track in enumerate(body["tracks"]):
            missing_t = required_track - set(track.keys())
            assert not missing_t, f"Track {i} missing fields: {missing_t}"
        print(f"✅ Response structure validated: {list(body.keys())}")

    def test_xcache_header_present(self, client):
        r = client.post("/api/generate", json={"mood": "focus mode"})
        assert r.status_code == 200
        assert "x-cache" in r.headers, f"X-Cache header missing. Headers: {dict(r.headers)}"
        assert r.headers["x-cache"].upper() in ("HIT", "MISS")
        print(f"✅ X-Cache header present: {r.headers['x-cache']}")
