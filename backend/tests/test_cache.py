"""
Unit tests for the ``normalize_mood`` helper in ``cache.py``.

Covers:
- Whitespace handling (leading/trailing strip, internal collapse)
- Lowercasing
- ASCII punctuation removal
- Deterministic output (same logical input → same key)
- Combinations of the above transformations
"""

from __future__ import annotations

import sys
import os
import string

# Ensure backend/ is on sys.path when tests are run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from cache import normalize_mood


# ---------------------------------------------------------------------------
# Whitespace handling
# ---------------------------------------------------------------------------


class TestNormalizeMoodWhitespace:
    """normalize_mood must strip edge whitespace and collapse internal runs."""

    def test_strips_leading_whitespace(self):
        assert normalize_mood("   happy") == "happy"

    def test_strips_trailing_whitespace(self):
        assert normalize_mood("happy   ") == "happy"

    def test_strips_both_ends(self):
        assert normalize_mood("  happy  ") == "happy"

    def test_collapses_internal_spaces(self):
        assert normalize_mood("driving  through   rain") == "driving through rain"

    def test_collapses_tabs(self):
        assert normalize_mood("driving\tthrough\train") == "driving through rain"

    def test_collapses_newlines(self):
        assert normalize_mood("sad\nand\nlonely") == "sad and lonely"

    def test_collapses_mixed_whitespace(self):
        # Whitespace is collapsed BEFORE punctuation is removed, so:
        # "3am  \t can't\nsleep"
        #   → strip → "3am  \t can't\nsleep"
        #   → collapse whitespace → "3am can't sleep"
        #   → lowercase → "3am can't sleep"
        #   → remove punctuation (apostrophe) → "3am cant sleep"
        assert normalize_mood("3am  \t can't\nsleep") == "3am cant sleep"

    def test_only_whitespace_returns_empty_string(self):
        """After stripping, a spaces-only string becomes empty."""
        assert normalize_mood("   ") == ""

    def test_empty_string_returns_empty_string(self):
        assert normalize_mood("") == ""


# ---------------------------------------------------------------------------
# Lowercasing
# ---------------------------------------------------------------------------


class TestNormalizeMoodLowercase:
    """normalize_mood must lowercase all characters."""

    def test_uppercase(self):
        assert normalize_mood("HAPPY") == "happy"

    def test_mixed_case(self):
        assert normalize_mood("Driving Through Rain") == "driving through rain"

    def test_all_caps_phrase(self):
        assert normalize_mood("LATE NIGHT VIBES") == "late night vibes"

    def test_camel_case(self):
        assert normalize_mood("LatNightVibes") == "latnightvibes"

    def test_already_lowercase_unchanged(self):
        assert normalize_mood("already lowercase") == "already lowercase"


# ---------------------------------------------------------------------------
# Punctuation removal
# ---------------------------------------------------------------------------


class TestNormalizeMoodPunctuation:
    """normalize_mood must remove all ASCII punctuation characters."""

    def test_removes_apostrophe(self):
        assert normalize_mood("can't") == "cant"

    def test_removes_exclamation(self):
        assert normalize_mood("happy!") == "happy"

    def test_removes_question_mark(self):
        assert normalize_mood("why?") == "why"

    def test_removes_ellipsis(self):
        assert normalize_mood("3am can't sleep...") == "3am cant sleep"

    def test_removes_comma(self):
        assert normalize_mood("sad, lonely") == "sad lonely"

    def test_removes_hyphen(self):
        assert normalize_mood("post-breakup") == "postbreakup"

    def test_removes_parentheses(self):
        assert normalize_mood("driving (at night)") == "driving at night"

    def test_removes_all_ascii_punctuation(self):
        """Every character in string.punctuation must be removed."""
        all_punct = string.punctuation  # !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
        result = normalize_mood(all_punct)
        assert result == ""

    def test_punctuation_only_string(self):
        assert normalize_mood("!!!") == ""

    def test_preserves_non_ascii_characters(self):
        """Unicode characters (e.g. accented letters, emoji) are NOT in string.punctuation
        so they survive the translation step."""
        result = normalize_mood("café vibes ☕")
        assert "café" in result
        assert "vibes" in result

    def test_numbers_preserved(self):
        """Digits are not punctuation and must survive."""
        assert normalize_mood("3am") == "3am"


# ---------------------------------------------------------------------------
# Determinism / cache-key consistency
# ---------------------------------------------------------------------------


class TestNormalizeMoodDeterminism:
    """Semantically equivalent inputs must produce identical normalised strings."""

    def test_same_input_same_output(self):
        mood = "driving through rain"
        assert normalize_mood(mood) == normalize_mood(mood)

    def test_case_variants_equal(self):
        assert normalize_mood("Happy") == normalize_mood("happy")
        assert normalize_mood("HAPPY") == normalize_mood("happy")
        assert normalize_mood("HaPPy") == normalize_mood("happy")

    def test_whitespace_variants_equal(self):
        assert normalize_mood("3am cant sleep") == normalize_mood("  3am  cant  sleep  ")

    def test_punctuation_variants_equal(self):
        """Adding or removing punctuation around the same words → same key."""
        # Apostrophe removal: "can't" and "cant" produce the same key
        assert normalize_mood("3am can't sleep") == normalize_mood("3am cant sleep")
        # Dots between words are removed without inserting spaces, so
        # "driving...through...rain" → "drivingthroughrain" (no spaces remain)
        assert normalize_mood("driving...through...rain") == "drivingthroughrain"
        # Dots after spaces are just removed; adjacent spaces are already collapsed
        assert normalize_mood("driving... through... rain") == normalize_mood("driving through rain")

    def test_combined_variants_equal(self):
        """Mixed case + extra spaces + punctuation should all normalise identically."""
        v1 = normalize_mood("3am Can't Sleep")
        v2 = normalize_mood("  3AM  CAN'T  SLEEP  ")
        v3 = normalize_mood("3am cant sleep")
        assert v1 == v2 == v3

    def test_tab_and_space_equal(self):
        """Tabs and spaces are both whitespace; collapsed to single space."""
        assert normalize_mood("word1\tword2") == normalize_mood("word1 word2")

    def test_newline_and_space_equal(self):
        assert normalize_mood("word1\nword2") == normalize_mood("word1 word2")

    def test_multiple_calls_idempotent(self):
        """Calling normalize_mood twice on the same input is idempotent."""
        mood = "  Late Night VIBES...  "
        once = normalize_mood(mood)
        twice = normalize_mood(once)
        assert once == twice


# ---------------------------------------------------------------------------
# Parametrised edge-case roundup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Basic
        ("happy", "happy"),
        ("Happy", "happy"),
        ("HAPPY", "happy"),
        # Whitespace
        ("  happy  ", "happy"),
        ("happy   day", "happy day"),
        # Punctuation
        ("happy!", "happy"),
        ("it's raining", "its raining"),
        ("post-rain calm", "postrain calm"),
        # Combo: 3am scenario
        ("3am Can't Sleep", "3am cant sleep"),
        ("  3AM  CAN'T  SLEEP...  ", "3am cant sleep"),
        # Driving scenario
        ("Driving Through Rain", "driving through rain"),
        ("DRIVING...THROUGH...RAIN", "drivingthroughrain"),  # dots removed, no spaces inserted
        # Empty / whitespace only
        ("", ""),
        ("   ", ""),
        # Numbers
        ("2am vibes", "2am vibes"),
        # Punctuation at boundaries
        ("...mood...", "mood"),
    ],
)
def test_normalize_mood_parametrized(raw: str, expected: str):
    assert normalize_mood(raw) == expected
