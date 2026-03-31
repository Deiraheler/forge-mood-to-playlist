import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import ai_service
from config import settings
from models import MoodRequest, PlaylistResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="Mood-to-Playlist API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/generate", response_model=PlaylistResponse, status_code=200)
async def generate_playlist(request: MoodRequest) -> PlaylistResponse:
    """
    Generate a mood-based playlist.

    - **mood**: A mood or situation string (1–200 characters). Pydantic enforces
      this; invalid input returns HTTP 422 automatically.
    - Returns a ``PlaylistResponse`` with playlist name, description, and tracks.
    - Returns HTTP 500 if the AI service fails.
    """
    # Enforce the 200-char cap at the endpoint level (models.py allows up to 500;
    # we tighten that here as per the task spec).
    if len(request.mood) > 200:
        raise HTTPException(
            status_code=422,
            detail="mood must be 200 characters or fewer.",
        )

    try:
        playlist = await ai_service.generate_playlist(request.mood)
        return playlist
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
