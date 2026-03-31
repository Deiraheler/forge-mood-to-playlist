"""
AI service module for generating mood-based playlists via OpenAI.

Retry strategy
--------------
- Transient OpenAI API errors (rate limits, server errors, network issues) are
  retried up to MAX_ATTEMPTS times with exponential backoff.
- Malformed JSON responses from the LLM trigger an immediate re-request (up to
  MAX_ATTEMPTS total attempts) so the model gets another chance to reply
  correctly.
- Permanent failures (auth errors, missing keys after all retries) raise
  fastapi.HTTPException with an appropriate status code so callers receive a
  clean HTTP error rather than an unhandled exception.
"""

import json
import logging

import openai
from fastapi import HTTPException
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    RetryError,
)

from config import settings
from models import Track, PlaylistResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ATTEMPTS = 3
RETRY_MIN_WAIT = 1   # seconds — first back-off delay
RETRY_MAX_WAIT = 10  # seconds — upper cap for back-off

# OpenAI exception types that indicate a transient failure worth retrying.
_TRANSIENT_OPENAI_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
)

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

_client: openai.AsyncOpenAI | None = None


def _get_client() -> openai.AsyncOpenAI:
    """Lazily initialise the AsyncOpenAI client so tests can patch settings."""
    global _client
    if _client is None:
        logger.debug("Initialising AsyncOpenAI client")
        _client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert music curator with deep knowledge of songs across all genres, \
decades, and cultures. Your specialty is crafting emotionally resonant playlists \
that perfectly match a listener's mood or situation.

When given a mood or situation, you must respond with a JSON object — no markdown, \
no prose, no code fences — using exactly this structure:

{
  "playlist_name": "<creative, evocative playlist name>",
  "description": "<2-3 sentence overall vibe description that captures the feeling>",
  "tracks": [
    {
      "title": "<exact song title>",
      "artist": "<exact artist or band name>",
      "vibe": "<1-2 sentence explanation of why this track fits the mood>"
    }
  ]
}

Rules:
- Return between 10 and 15 tracks.
- Choose real songs by real artists only. No fictional tracks.
- Vary the era, tempo, and genre to create a journey through the mood.
- The playlist_name must be poetic and unique — avoid generic titles.
- Respond with valid JSON only. Do not wrap in markdown code blocks.
"""

# ---------------------------------------------------------------------------
# Internal helpers with retry decorators
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type(_TRANSIENT_OPENAI_ERRORS),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _call_openai(mood: str) -> str:
    """
    Make a single OpenAI chat completion request and return the raw content string.

    Decorated with tenacity to automatically retry on transient API errors
    (rate limits, connection errors, timeouts, internal server errors) with
    exponential back-off.

    Parameters
    ----------
    mood : str
        The mood/situation string to pass to the model.

    Returns
    -------
    str
        Raw content string from the first choice of the completion response.

    Raises
    ------
    openai.AuthenticationError
        Re-raised immediately (not retried) when the API key is invalid.
    openai.RateLimitError / openai.APIConnectionError / openai.APITimeoutError
    / openai.InternalServerError
        Retried up to MAX_ATTEMPTS times before being re-raised.
    """
    client = _get_client()
    logger.info("Calling OpenAI API for mood: %r (attempt will be tracked by tenacity)", mood)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.9,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Generate a playlist for this mood/situation: {mood}",
            },
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or ""
    logger.debug("Raw OpenAI response (%d chars): %s", len(raw), raw[:200])
    return raw


def _parse_playlist(raw: str, mood: str) -> PlaylistResponse:
    """
    Parse and validate a raw JSON string into a PlaylistResponse.

    Parameters
    ----------
    raw : str
        Raw JSON string received from OpenAI.
    mood : str
        Original mood string (injected into the response model).

    Returns
    -------
    PlaylistResponse
        Fully validated playlist model.

    Raises
    ------
    json.JSONDecodeError
        If *raw* is not valid JSON (caller may retry).
    ValueError
        If required top-level keys are absent or track data is malformed.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "JSON parse failed (will retry if attempts remain): %s | raw excerpt: %.200s",
            exc,
            raw,
        )
        raise  # re-raise so the outer loop can decide whether to retry

    missing_keys = [k for k in ("playlist_name", "description", "tracks") if k not in data]
    if missing_keys:
        logger.warning("OpenAI response missing required keys %s — will retry", missing_keys)
        raise ValueError(f"OpenAI response missing required keys: {missing_keys}")

    if not isinstance(data["tracks"], list) or len(data["tracks"]) == 0:
        logger.warning("OpenAI returned empty or non-list tracks — will retry")
        raise ValueError("OpenAI response 'tracks' is empty or not a list")

    try:
        tracks = [
            Track(
                title=t["title"],
                artist=t["artist"],
                vibe=t["vibe"],
            )
            for t in data["tracks"]
        ]
    except (KeyError, TypeError) as exc:
        logger.warning("Track data malformed: %s — will retry", exc)
        raise ValueError(f"Track data malformed: {exc}") from exc

    logger.info(
        "Successfully parsed playlist %r with %d tracks",
        data["playlist_name"],
        len(tracks),
    )

    return PlaylistResponse(
        mood=mood,
        playlist_name=data["playlist_name"],
        description=data["description"],
        tracks=tracks,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_playlist(mood: str) -> PlaylistResponse:
    """
    Generate a Spotify-style playlist for the given mood using OpenAI.

    Implements a multi-layer retry strategy:
    - Transient OpenAI API errors are retried automatically by ``_call_openai``
      (via tenacity) with exponential back-off.
    - JSON parse / structure errors trigger a full re-request (new API call)
      up to MAX_ATTEMPTS total times, in case the model produces a malformed
      response on a given attempt.

    Parameters
    ----------
    mood : str
        The mood or situation description provided by the user.

    Returns
    -------
    PlaylistResponse
        A fully validated Pydantic model containing the playlist.

    Raises
    ------
    fastapi.HTTPException
        - 502 Bad Gateway if all retry attempts are exhausted due to OpenAI
          API errors.
        - 503 Service Unavailable if the model repeatedly returns malformed
          JSON/structure after MAX_ATTEMPTS retries.
        - 401 Unauthorized if the OpenAI API key is invalid.
        - 500 Internal Server Error for unexpected failures.
    """
    logger.info("generate_playlist called | mood=%r", mood)

    last_exc: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info("Playlist generation attempt %d/%d", attempt, MAX_ATTEMPTS)

        # ── Step 1: Call OpenAI (transient errors are retried internally) ──
        try:
            raw = await _call_openai(mood)
        except openai.AuthenticationError as exc:
            logger.error("OpenAI authentication failed — check OPENAI_API_KEY: %s", exc)
            raise HTTPException(
                status_code=401,
                detail="OpenAI authentication failed. Please check the API key.",
            ) from exc
        except RetryError as exc:
            # tenacity exhausted its own retries inside _call_openai
            logger.error(
                "OpenAI API unreachable after internal retries (attempt %d/%d): %s",
                attempt,
                MAX_ATTEMPTS,
                exc,
            )
            last_exc = exc
            # Don't break — outer loop gives extra chances for parse errors;
            # for API errors all retries are already spent, so break now.
            break
        except _TRANSIENT_OPENAI_ERRORS as exc:
            # Shouldn't normally reach here (tenacity reraises), but guard anyway.
            logger.error("Transient OpenAI error on attempt %d: %s", attempt, exc)
            last_exc = exc
            break
        except openai.OpenAIError as exc:
            logger.error("Permanent OpenAI error on attempt %d: %s", attempt, exc)
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI API error: {exc}",
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error calling OpenAI on attempt %d: %s", attempt, exc)
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while calling the AI service.",
            ) from exc

        # ── Step 2: Parse and validate the response ──
        try:
            return _parse_playlist(raw, mood)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Parse/validation error on attempt %d/%d: %s",
                attempt,
                MAX_ATTEMPTS,
                exc,
            )
            last_exc = exc
            # Continue outer loop to retry the full API call with a fresh response.
            continue

    # ── All attempts exhausted ──
    logger.error(
        "All %d playlist generation attempts failed. Last error: %s",
        MAX_ATTEMPTS,
        last_exc,
    )

    if isinstance(last_exc, (RetryError, *_TRANSIENT_OPENAI_ERRORS)):
        raise HTTPException(
            status_code=502,
            detail="The AI service is temporarily unavailable. Please try again later.",
        )

    raise HTTPException(
        status_code=503,
        detail=(
            "The AI service returned an invalid response after multiple attempts. "
            "Please try again."
        ),
    )
