import logging

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

import ai_service
from cache import get_cached_playlist, get_redis, set_cached_playlist
from config import settings
from models import MoodRequest, PlaylistResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mood-to-Playlist API",
    version="1.0.0",
    description=(
        "Generate Spotify-style playlists from a mood or situation description using OpenAI. "
        "No authentication required. Responses are cached in Redis for repeated moods.\n\n"
        "## Quick Start\n"
        "Send a `POST /api/generate` request with a JSON body containing a `mood` string "
        "(1–200 characters) and receive a curated 10–15 track playlist with song titles, "
        "artists, and per-track vibe descriptions.\n\n"
        "## Rate Limiting\n"
        "There is no built-in rate limiting in this version. For production deployments, "
        "apply rate limiting at the reverse-proxy level (e.g. nginx `limit_req` or an API "
        "gateway). Redis caching significantly reduces upstream OpenAI calls for repeated moods.\n\n"
        "## Caching\n"
        "Responses are cached in Redis using the mood string as the key. "
        "Cache hits return instantly and include `\"cached\": true` in the response body "
        "and an `X-Cache: HIT` response header."
    ),
    contact={
        "name": "Mood-to-Playlist",
    },
    license_info={
        "name": "MIT",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["Health"], summary="Health check")
async def health():
    """
    Check that the API is running.

    Returns a simple `{"status": "ok"}` payload. Use this endpoint for
    liveness probes (e.g. Docker HEALTHCHECK, Kubernetes liveness probe).
    It does **not** verify Redis or OpenAI connectivity — it only confirms
    the web process is accepting requests.
    """
    return {"status": "ok"}


@app.post(
    "/api/generate",
    response_model=PlaylistResponse,
    status_code=200,
    tags=["Playlist"],
    summary="Generate a mood-based playlist",
    responses={
        200: {"description": "Playlist successfully generated or returned from cache."},
        422: {"description": "Validation error — mood is missing, empty, or exceeds 200 characters."},
        500: {"description": "AI service error — OpenAI returned an unexpected or unparseable response."},
    },
)
async def generate_playlist(
    request: MoodRequest,
    http_response: Response,
    redis: Redis | None = Depends(get_redis),
) -> PlaylistResponse:
    """
    Generate a curated 10–15 track playlist that matches the provided mood or situation.

    **Request body:**
    - `mood` *(string, required)* — A free-text description of a mood or situation,
      between 1 and 200 characters. Examples: `"3am can't sleep"`,
      `"driving through rain"`, `"summer bbq with friends"`.

    **Response body:**
    - `mood` — Echo of the input mood string.
    - `playlist_name` — A creative, evocative name for the playlist.
    - `description` — A 2–3 sentence overall vibe description.
    - `tracks` — List of 10–15 track objects, each with `title`, `artist`, and `vibe`.
    - `cached` — `true` if this result was served from Redis cache, `false` otherwise.

    **Response headers:**
    - `X-Cache: HIT` — Response was served from Redis cache.
    - `X-Cache: MISS` — Response was freshly generated via OpenAI.

    **Error codes:**
    - `422 Unprocessable Entity` — The `mood` field failed validation (missing, blank,
      or longer than 200 characters). The response body contains a `detail` array
      with field-level error messages from Pydantic.
    - `500 Internal Server Error` — The OpenAI service returned an unexpected or
      malformed response after all retry attempts were exhausted.
    """
    # Enforce the 200-char cap at the endpoint level (models.py allows up to 500;
    # we tighten that here as per the task spec).
    if len(request.mood) > 200:
        raise HTTPException(
            status_code=422,
            detail="mood must be 200 characters or fewer.",
        )

    # --- Cache lookup ---
    cached_playlist = await get_cached_playlist(redis, request.mood)
    if cached_playlist is not None:
        http_response.headers["X-Cache"] = "HIT"
        cached_playlist.cached = True
        return cached_playlist

    # --- Cache miss: generate via AI ---
    try:
        playlist = await ai_service.generate_playlist(request.mood)
    except ValueError as exc:
        logger.error("Playlist generation returned invalid data: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate playlist: the AI returned an unexpected response.",
        ) from exc
    except RuntimeError as exc:
        logger.error("Playlist generation failed (runtime): %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate playlist: upstream AI service error.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during playlist generation: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while generating the playlist.",
        ) from exc

    # Store fresh result in cache (fire-and-forget; errors logged inside helper)
    playlist.cached = False
    await set_cached_playlist(redis, request.mood, playlist)

    http_response.headers["X-Cache"] = "MISS"
    return playlist
