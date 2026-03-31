"""
AI service module for generating mood-based playlists via OpenAI.
"""

import json
import logging
from openai import AsyncOpenAI

from config import settings
from models import Track, PlaylistResponse

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """Lazily initialise the AsyncOpenAI client so tests can patch settings."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


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


async def generate_playlist(mood: str) -> PlaylistResponse:
    """
    Call OpenAI to generate a playlist for the given mood string.

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
    ValueError
        If the API response cannot be parsed as valid playlist JSON.
    RuntimeError
        If the OpenAI API call itself fails.
    """
    client = _get_client()

    logger.info("Generating playlist for mood: %r", mood)

    try:
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
    except Exception as exc:
        logger.error("OpenAI API call failed: %s", exc)
        raise RuntimeError(f"OpenAI API call failed: {exc}") from exc

    raw = response.choices[0].message.content or ""
    logger.debug("Raw OpenAI response: %s", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAI JSON response: %s\nRaw: %s", exc, raw)
        raise ValueError(f"Invalid JSON from OpenAI: {exc}") from exc

    # Validate required top-level keys
    missing = [k for k in ("playlist_name", "description", "tracks") if k not in data]
    if missing:
        raise ValueError(f"OpenAI response missing required keys: {missing}")

    tracks = [
        Track(
            title=t["title"],
            artist=t["artist"],
            vibe=t["vibe"],
        )
        for t in data["tracks"]
    ]

    return PlaylistResponse(
        mood=mood,
        playlist_name=data["playlist_name"],
        description=data["description"],
        tracks=tracks,
    )
