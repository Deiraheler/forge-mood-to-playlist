"""
Tests for ai_service.generate_playlist.

Coverage
--------
- Happy path: valid LLM response returns a correct PlaylistResponse.
- Prompt verification: the user mood string appears in the prompt sent to OpenAI.
- Retry on transient failure: RateLimitError is retried; success on 2nd attempt.
- All transient failures exhausted → HTTPException 502.
- Malformed JSON from LLM: retried up to MAX_ATTEMPTS, then HTTPException 503.
- AuthenticationError → HTTPException 401 (no retry).
- _parse_playlist directly: valid JSON, bad JSON, missing keys.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import openai
import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# sys.path is already adjusted by conftest.py, so bare imports work here.
# ---------------------------------------------------------------------------
import ai_service
from ai_service import generate_playlist, _parse_playlist, MAX_ATTEMPTS
from models import PlaylistResponse, Track


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOOD = "3am can't sleep"

VALID_LLM_JSON = json.dumps(
    {
        "playlist_name": "Insomnia Echoes",
        "description": "Quiet tracks for the small hours.",
        "tracks": [
            {"title": f"Song {i}", "artist": f"Artist {i}", "vibe": f"Vibe {i}"}
            for i in range(10)
        ],
    }
)


def _make_openai_response(content: str) -> MagicMock:
    """Build a minimal mock that looks like an openai ChatCompletion response."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# _parse_playlist unit tests (synchronous helper, no async needed)
# ---------------------------------------------------------------------------


class TestParsePlaylist:
    def test_valid_json_returns_playlist_response(self):
        result = _parse_playlist(VALID_LLM_JSON, MOOD)
        assert isinstance(result, PlaylistResponse)
        assert result.mood == MOOD
        assert result.playlist_name == "Insomnia Echoes"
        assert len(result.tracks) == 10
        assert result.tracks[0].title == "Song 0"

    def test_mood_is_injected_into_response(self):
        result = _parse_playlist(VALID_LLM_JSON, MOOD)
        assert result.mood == MOOD

    def test_malformed_json_raises_json_decode_error(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_playlist("not valid json {{", MOOD)

    def test_missing_playlist_name_raises_value_error(self):
        data = json.dumps(
            {
                "description": "Some description",
                "tracks": [
                    {"title": "S", "artist": "A", "vibe": "V"} for _ in range(10)
                ],
            }
        )
        with pytest.raises((ValueError, KeyError)):
            _parse_playlist(data, MOOD)

    def test_missing_tracks_raises_value_error(self):
        data = json.dumps(
            {
                "playlist_name": "Test",
                "description": "desc",
            }
        )
        with pytest.raises((ValueError, KeyError)):
            _parse_playlist(data, MOOD)

    def test_malformed_track_entry_raises_value_error(self):
        """A track dict missing required fields should raise ValueError."""
        data = json.dumps(
            {
                "playlist_name": "Test",
                "description": "desc",
                "tracks": [{"title": "Only Title"}],  # missing artist & vibe
            }
        )
        with pytest.raises((ValueError, KeyError)):
            _parse_playlist(data, MOOD)


# ---------------------------------------------------------------------------
# generate_playlist integration tests (async, mocked _call_openai)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGeneratePlaylist:

    async def test_valid_response_returns_playlist_response(self):
        """Happy path: _call_openai returns valid JSON → PlaylistResponse."""
        with patch("ai_service._call_openai", new=AsyncMock(return_value=VALID_LLM_JSON)):
            result = await generate_playlist(MOOD)

        assert isinstance(result, PlaylistResponse)
        assert result.mood == MOOD
        assert result.playlist_name == "Insomnia Echoes"
        assert len(result.tracks) == 10

    async def test_mood_string_present_in_openai_prompt(self):
        """The mood string must be forwarded to the OpenAI API call."""
        captured_calls: list[dict] = []

        async def _fake_create(**kwargs):
            captured_calls.append(kwargs)
            return _make_openai_response(VALID_LLM_JSON)

        mock_client = MagicMock()
        mock_client.chat.completions.create = _fake_create

        with patch("ai_service._get_client", return_value=mock_client):
            # Reset the module-level cached client so _get_client is called fresh
            original_client = ai_service._client
            ai_service._client = None
            try:
                result = await generate_playlist(MOOD)
            finally:
                ai_service._client = original_client

        assert len(captured_calls) == 1
        messages = captured_calls[0]["messages"]
        user_message = next(m for m in messages if m["role"] == "user")
        assert MOOD in user_message["content"]

    async def test_retry_on_transient_error_handled_by_tenacity(self):
        """
        Tenacity handles retries *inside* _call_openai for transient errors.
        We verify that when _call_openai raises RateLimitError once internally
        but then succeeds (simulated by the real tenacity retry), the outer
        generate_playlist still returns a valid PlaylistResponse.

        We test this by patching the OpenAI client's create method directly
        so tenacity can retry it: fail on attempt 1, succeed on attempt 2.
        """
        call_count = 0

        async def _flaky_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise openai.RateLimitError(
                    message="rate limited",
                    response=MagicMock(status_code=429, headers={}),
                    body={},
                )
            return _make_openai_response(VALID_LLM_JSON)

        mock_client = MagicMock()
        mock_client.chat.completions.create = _flaky_create

        original_client = ai_service._client
        ai_service._client = mock_client
        try:
            result = await generate_playlist(MOOD)
        finally:
            ai_service._client = original_client

        assert isinstance(result, PlaylistResponse)
        assert result.mood == MOOD
        assert call_count == 2  # tenacity retried once

    async def test_all_transient_failures_raise_502(self):
        """If _call_openai always raises RateLimitError (via RetryError), expect 502."""
        from tenacity import RetryError

        retry_error = RetryError(last_attempt=MagicMock())

        with patch("ai_service._call_openai", new=AsyncMock(side_effect=retry_error)):
            with pytest.raises(HTTPException) as exc_info:
                await generate_playlist(MOOD)

        assert exc_info.value.status_code == 502

    async def test_malformed_json_all_attempts_raises_503(self):
        """If LLM always returns bad JSON, all retries exhausted → HTTPException 503."""
        with patch(
            "ai_service._call_openai",
            new=AsyncMock(return_value="this is not json }{"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await generate_playlist(MOOD)

        assert exc_info.value.status_code == 503

    async def test_malformed_json_retried_max_attempts_times(self):
        """_call_openai is called MAX_ATTEMPTS times when JSON is always malformed."""
        mock_call = AsyncMock(return_value="bad json {{")

        with patch("ai_service._call_openai", mock_call):
            with pytest.raises(HTTPException) as exc_info:
                await generate_playlist(MOOD)

        assert exc_info.value.status_code == 503
        assert mock_call.call_count == MAX_ATTEMPTS

    async def test_malformed_json_succeeds_on_last_attempt(self):
        """Bad JSON on first N-1 attempts, valid JSON on last → success."""
        attempt = 0

        async def _eventually_valid(mood: str) -> str:
            nonlocal attempt
            attempt += 1
            if attempt < MAX_ATTEMPTS:
                return "bad json {{"
            return VALID_LLM_JSON

        with patch("ai_service._call_openai", side_effect=_eventually_valid):
            result = await generate_playlist(MOOD)

        assert isinstance(result, PlaylistResponse)
        assert result.mood == MOOD

    async def test_authentication_error_raises_401(self):
        """AuthenticationError (bad API key) → HTTPException 401, no retry."""
        auth_exc = openai.AuthenticationError(
            message="invalid api key",
            response=MagicMock(status_code=401, headers={}),
            body={},
        )

        with patch("ai_service._call_openai", new=AsyncMock(side_effect=auth_exc)):
            with pytest.raises(HTTPException) as exc_info:
                await generate_playlist(MOOD)

        assert exc_info.value.status_code == 401

    async def test_result_has_no_cached_flag_set(self):
        """generate_playlist itself does not set cached=True (cache layer is separate)."""
        with patch("ai_service._call_openai", new=AsyncMock(return_value=VALID_LLM_JSON)):
            result = await generate_playlist(MOOD)

        assert result.cached is False

    async def test_tracks_have_required_fields(self):
        """Every track in the response has title, artist, and vibe."""
        with patch("ai_service._call_openai", new=AsyncMock(return_value=VALID_LLM_JSON)):
            result = await generate_playlist(MOOD)

        for track in result.tracks:
            assert track.title
            assert track.artist
            assert track.vibe
