from pydantic import BaseModel, Field


class MoodRequest(BaseModel):
    mood: str = Field(..., min_length=1, max_length=500, description="The mood or situation to generate a playlist for")


class Track(BaseModel):
    title: str = Field(..., description="The song title")
    artist: str = Field(..., description="The artist name")
    vibe: str = Field(..., description="A short description of why this track fits the mood")


class PlaylistResponse(BaseModel):
    mood: str = Field(..., description="The original mood input from the user")
    playlist_name: str = Field(..., description="A creative name for the playlist")
    description: str = Field(..., description="An overall vibe description for the playlist")
    tracks: list[Track] = Field(..., description="List of tracks in the playlist")


__all__ = ["MoodRequest", "Track", "PlaylistResponse"]
