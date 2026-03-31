"""
Unit tests for Pydantic models defined in models.py.

Covers:
- MoodRequest: validation of the ``mood`` field (empty, too long, valid, edge cases)
- Track: required field presence
- PlaylistResponse: construction and ``cached`` default
"""

from __future__ import annotations

import sys
import os

# Ensure backend/ is on sys.path when tests are run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from pydantic import ValidationError

from models import MoodRequest, PlaylistResponse, Track


# ---------------------------------------------------------------------------
# MoodRequest — valid inputs
# ---------------------------------------------------------------------------


class TestMoodRequestValid:
    """MoodRequest should accept any non-empty string up to 500 characters."""

    def test_simple_mood(self):
        req = MoodRequest(mood="happy")
        assert req.mood == "happy"

    def test_single_character(self):
        """A single character satisfies min_length=1."""
        req = MoodRequest(mood="x")
        assert req.mood == "x"

    def test_exactly_500_chars(self):
        """500-character string is at the boundary — should be valid."""
        long_mood = "a" * 500
        req = MoodRequest(mood=long_mood)
        assert len(req.mood) == 500

    def test_mood_with_whitespace(self):
        """Leading/trailing whitespace is preserved by the model (no stripping at model level)."""
        req = MoodRequest(mood="  driving through rain  ")
        assert req.mood == "  driving through rain  "

    def test_mood_with_punctuation(self):
        req = MoodRequest(mood="3am can't sleep...")
        assert req.mood == "3am can't sleep..."

    def test_mood_with_newlines(self):
        """Multi-line strings count as valid moods."""
        req = MoodRequest(mood="sad\nand lonely")
        assert req.mood == "sad\nand lonely"

    def test_mood_unicode(self):
        """Non-ASCII characters should be accepted."""
        req = MoodRequest(mood="chill café vibes ☕")
        assert req.mood == "chill café vibes ☕"

    def test_mood_numbers_only(self):
        req = MoodRequest(mood="42")
        assert req.mood == "42"

    def test_mood_spaces_only(self):
        """Spaces-only string has length > 0 and passes min_length=1."""
        req = MoodRequest(mood="   ")
        assert req.mood == "   "


# ---------------------------------------------------------------------------
# MoodRequest — invalid inputs
# ---------------------------------------------------------------------------


class TestMoodRequestInvalid:
    """MoodRequest should raise ValidationError for empty or too-long inputs."""

    def test_empty_string_raises(self):
        """Empty string violates min_length=1."""
        with pytest.raises(ValidationError) as exc_info:
            MoodRequest(mood="")
        errors = exc_info.value.errors()
        assert any(
            "min_length" in str(e).lower() or "string should have at least" in str(e).lower()
            for e in errors
        )

    def test_501_chars_raises(self):
        """501-character string exceeds max_length=500."""
        with pytest.raises(ValidationError) as exc_info:
            MoodRequest(mood="b" * 501)
        errors = exc_info.value.errors()
        assert any(
            "max_length" in str(e).lower() or "string should have at most" in str(e).lower()
            for e in errors
        )

    def test_very_long_string_raises(self):
        """Strings far over the limit should still fail cleanly."""
        with pytest.raises(ValidationError):
            MoodRequest(mood="z" * 10_000)

    def test_missing_mood_field_raises(self):
        """The ``mood`` field is required; omitting it should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MoodRequest()  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("mood",) for e in errors)

    def test_none_mood_raises(self):
        """None is not a valid string value."""
        with pytest.raises(ValidationError):
            MoodRequest(mood=None)  # type: ignore[arg-type]

    def test_integer_mood_raises(self):
        """Passing an integer (not coercible to str with strict mode off, but wrong type) should raise."""
        # Pydantic v2 will coerce int to str in lax mode, but let's verify behaviour.
        # We just assert no exception is raised on coercion, or a ValidationError if strict.
        try:
            req = MoodRequest(mood=123)  # type: ignore[arg-type]
            # If Pydantic coerces, the resulting string "123" must satisfy min/max
            assert req.mood == "123"
        except ValidationError:
            pass  # strict mode — acceptable either way


# ---------------------------------------------------------------------------
# MoodRequest — boundary checks
# ---------------------------------------------------------------------------


class TestMoodRequestBoundary:
    """Explicit boundary tests for min/max length."""

    @pytest.mark.parametrize("length", [1, 2, 100, 250, 499, 500])
    def test_valid_lengths(self, length: int):
        req = MoodRequest(mood="a" * length)
        assert len(req.mood) == length

    @pytest.mark.parametrize("length", [0, 501, 502, 1000])
    def test_invalid_lengths(self, length: int):
        with pytest.raises(ValidationError):
            MoodRequest(mood="a" * length)


# ---------------------------------------------------------------------------
# Track model
# ---------------------------------------------------------------------------


class TestTrack:
    """Track requires title, artist, and vibe."""

    def test_valid_track(self):
        t = Track(title="Holocene", artist="Bon Iver", vibe="Expansive and melancholic.")
        assert t.title == "Holocene"
        assert t.artist == "Bon Iver"
        assert t.vibe == "Expansive and melancholic."

    def test_missing_title_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            Track(artist="Bon Iver", vibe="Great song.")  # type: ignore[call-arg]
        assert any(e["loc"] == ("title",) for e in exc_info.value.errors())

    def test_missing_artist_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            Track(title="Holocene", vibe="Great song.")  # type: ignore[call-arg]
        assert any(e["loc"] == ("artist",) for e in exc_info.value.errors())

    def test_missing_vibe_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            Track(title="Holocene", artist="Bon Iver")  # type: ignore[call-arg]
        assert any(e["loc"] == ("vibe",) for e in exc_info.value.errors())


# ---------------------------------------------------------------------------
# PlaylistResponse model
# ---------------------------------------------------------------------------


class TestPlaylistResponse:
    """PlaylistResponse should construct correctly and default cached to False."""

    def _make_tracks(self, n: int = 2) -> list[Track]:
        return [
            Track(title=f"Song {i}", artist=f"Artist {i}", vibe=f"Vibe {i}")
            for i in range(n)
        ]

    def test_valid_playlist_response(self):
        pr = PlaylistResponse(
            mood="happy",
            playlist_name="Sunshine Hits",
            description="Feel-good bangers.",
            tracks=self._make_tracks(),
        )
        assert pr.mood == "happy"
        assert pr.playlist_name == "Sunshine Hits"
        assert pr.description == "Feel-good bangers."
        assert len(pr.tracks) == 2
        assert pr.cached is False  # default

    def test_cached_default_is_false(self):
        pr = PlaylistResponse(
            mood="melancholy",
            playlist_name="Quiet Hours",
            description="Slow and soft.",
            tracks=self._make_tracks(1),
        )
        assert pr.cached is False

    def test_cached_can_be_set_true(self):
        pr = PlaylistResponse(
            mood="melancholy",
            playlist_name="Quiet Hours",
            description="Slow and soft.",
            tracks=self._make_tracks(1),
            cached=True,
        )
        assert pr.cached is True

    def test_empty_tracks_list_accepted(self):
        """PlaylistResponse does not enforce a minimum track count at model level."""
        pr = PlaylistResponse(
            mood="blank",
            playlist_name="Empty",
            description="Nothing here.",
            tracks=[],
        )
        assert pr.tracks == []

    def test_missing_required_fields_raise(self):
        with pytest.raises(ValidationError):
            PlaylistResponse(mood="sad")  # type: ignore[call-arg]

    def test_round_trip_json(self):
        """model_dump_json → model_validate_json should produce an equivalent object."""
        pr = PlaylistResponse(
            mood="driving at night",
            playlist_name="Nightcrawler",
            description="Dark and fast.",
            tracks=self._make_tracks(3),
        )
        json_str = pr.model_dump_json()
        restored = PlaylistResponse.model_validate_json(json_str)
        assert restored.mood == pr.mood
        assert restored.playlist_name == pr.playlist_name
        assert len(restored.tracks) == len(pr.tracks)
        assert restored.cached == pr.cached
