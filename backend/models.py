from pydantic import BaseModel, Field


class MoodRequest(BaseModel):
    """Request body for the playlist generation endpoint."""

    mood: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="A free-text mood or situation description (1–200 characters recommended).",
        examples=["3am can't sleep", "driving through rain", "summer bbq with friends"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"mood": "3am can't sleep"},
                {"mood": "driving through rain"},
                {"mood": "summer bbq with friends"},
            ]
        }
    }


class Track(BaseModel):
    """A single track in a generated playlist."""

    title: str = Field(
        ...,
        description="The exact song title.",
        examples=["Holocene", "Motion Picture Soundtrack"],
    )
    artist: str = Field(
        ...,
        description="The exact artist or band name.",
        examples=["Bon Iver", "Radiohead"],
    )
    vibe: str = Field(
        ...,
        description="A 1–2 sentence explanation of why this track fits the mood.",
        examples=["Delicate and introspective; the sparse piano mirrors that wide-awake quiet."],
    )


class PlaylistResponse(BaseModel):
    """A fully generated mood-based playlist."""

    mood: str = Field(
        ...,
        description="Echo of the original mood input from the user.",
        examples=["3am can't sleep"],
    )
    playlist_name: str = Field(
        ...,
        description="A creative, evocative name for the playlist.",
        examples=["Sleepless Constellations"],
    )
    description: str = Field(
        ...,
        description="A 2–3 sentence overall vibe description capturing the emotional feel.",
        examples=[
            "The world is asleep but your mind won't stop. "
            "These tracks sit in that tender, too-honest hour — "
            "soft enough to think, vast enough to feel less alone."
        ],
    )
    tracks: list[Track] = Field(
        ...,
        description="Ordered list of 10–15 tracks that fit the mood.",
    )
    cached: bool = Field(
        default=False,
        description="True if this response was served from Redis cache; false if freshly generated.",
        examples=[False, True],
    )


__all__ = ["MoodRequest", "Track", "PlaylistResponse"]
