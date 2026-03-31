// TypeScript interfaces matching backend Pydantic models (backend/models.py)

export interface Track {
  title: string;
  artist: string;
  vibe: string;
}

export interface PlaylistResponse {
  mood: string;
  playlist_name: string;
  description: string;
  tracks: Track[];
  cached: boolean;
}

export interface ApiError {
  message: string;
  status?: number;
}

// Custom error class for typed error handling
export class PlaylistApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "PlaylistApiError";
    this.status = status;
  }
}

/**
 * POST /api/generate — generate a mood-based playlist.
 * Throws PlaylistApiError on network failure or non-2xx response.
 */
export async function generatePlaylist(mood: string): Promise<PlaylistResponse> {
  let response: Response;

  try {
    response = await fetch("/api/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ mood }),
    });
  } catch (err) {
    // Network-level failure (offline, DNS, CORS pre-flight, etc.)
    throw new PlaylistApiError(
      err instanceof Error ? err.message : "Network error — could not reach the server.",
    );
  }

  if (!response.ok) {
    // Try to extract a detail message from the JSON body (FastAPI error shape)
    let detail: string | undefined;
    try {
      const body = await response.json();
      detail = typeof body?.detail === "string" ? body.detail : undefined;
    } catch {
      // ignore JSON parse failure
    }

    throw new PlaylistApiError(
      detail ?? `Request failed with status ${response.status}.`,
      response.status,
    );
  }

  try {
    const data: PlaylistResponse = await response.json();
    return data;
  } catch {
    throw new PlaylistApiError("Failed to parse server response as JSON.");
  }
}
