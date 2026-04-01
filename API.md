# Mood-to-Playlist API Reference

Base URL (local dev): `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs` (Swagger UI) · `http://localhost:8000/redoc` (ReDoc)

---

## Endpoints

### `GET /api/health`

Liveness probe. Returns `200 OK` when the web process is accepting requests.  
Does **not** verify Redis or OpenAI connectivity.

**Response**

```json
{ "status": "ok" }
```

**curl**

```bash
curl http://localhost:8000/api/health
```

---

### `POST /api/generate`

Generate a curated 10–15 track playlist that matches the provided mood or situation.  
Responses are cached in Redis — repeated identical moods return instantly.

#### Request

| Field  | Type   | Required | Constraints          | Description                                   |
|--------|--------|----------|----------------------|-----------------------------------------------|
| `mood` | string | ✅ yes   | 1–200 chars, non-empty | Free-text mood or situation description     |

**Content-Type:** `application/json`

**Body schema**

```json
{
  "mood": "<string, 1–200 characters>"
}
```

**Examples**

```bash
# Minimal request
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"mood": "3am can'\''t sleep"}'
```

```bash
# Driving mood
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"mood": "driving through rain on a highway at night"}'
```

```bash
# Social mood
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"mood": "summer bbq with friends and cold drinks"}'
```

```bash
# Pretty-print with jq
curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"mood": "nostalgic Sunday morning"}' | jq .
```

---

#### Response — `200 OK`

| Field           | Type            | Description                                                        |
|-----------------|-----------------|--------------------------------------------------------------------|
| `mood`          | string          | Echo of the input mood string.                                     |
| `playlist_name` | string          | Creative, evocative playlist title.                                |
| `description`   | string          | 2–3 sentence overall vibe description.                             |
| `tracks`        | array of Track  | 10–15 ordered tracks (see Track object below).                     |
| `cached`        | boolean         | `true` if served from Redis cache; `false` if freshly generated.  |

**Track object**

| Field    | Type   | Description                                              |
|----------|--------|----------------------------------------------------------|
| `title`  | string | Exact song title.                                        |
| `artist` | string | Exact artist or band name.                               |
| `vibe`   | string | 1–2 sentence explanation of why the track fits the mood. |

**Response headers**

| Header    | Value  | Meaning                                |
|-----------|--------|----------------------------------------|
| `X-Cache` | `HIT`  | Response served from Redis cache.      |
| `X-Cache` | `MISS` | Response freshly generated via OpenAI. |

**Example response body**

```json
{
  "mood": "3am can't sleep",
  "playlist_name": "Sleepless Constellations",
  "description": "The world is asleep but your mind won't stop. These tracks sit in that tender, too-honest hour — soft enough to think, vast enough to feel less alone. Drift between wakefulness and wherever you need to go.",
  "tracks": [
    {
      "title": "Holocene",
      "artist": "Bon Iver",
      "vibe": "Delicate and introspective; the sparse instrumentation mirrors that wide-awake quiet of early morning."
    },
    {
      "title": "Motion Picture Soundtrack",
      "artist": "Radiohead",
      "vibe": "Fragile and searching — perfectly suited to the weightless sadness of a sleepless night."
    },
    {
      "title": "Lua",
      "artist": "Bright Eyes",
      "vibe": "Intimate confessional folk that feels like an honest 3am conversation with yourself."
    }
  ],
  "cached": false
}
```

---

#### Error Responses

All error responses follow FastAPI's standard format. The `detail` field is either a string (for application-level errors) or an array of objects (for Pydantic validation errors).

---

##### `422 Unprocessable Entity` — Validation Error

Returned when the request body fails validation: `mood` is missing, blank, or exceeds 200 characters.

```json
{
  "detail": [
    {
      "type": "string_too_long",
      "loc": ["body", "mood"],
      "msg": "String should have at most 500 characters",
      "input": "...",
      "ctx": { "max_length": 500 }
    }
  ]
}
```

**curl example — missing field**

```bash
curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
# → 422 with detail describing the missing "mood" field
```

**curl example — empty string**

```bash
curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"mood": ""}' | jq .
# → 422 with "String should have at least 1 character"
```

---

##### `500 Internal Server Error` — AI Service Error

Returned when the OpenAI service returns an unexpected or malformed response after all retry attempts are exhausted.

```json
{
  "detail": "Failed to generate playlist: the AI returned an unexpected response."
}
```

Possible `detail` values:

| Message | Cause |
|---|---|
| `"Failed to generate playlist: the AI returned an unexpected response."` | OpenAI returned invalid/unparseable JSON after all retries. |
| `"Failed to generate playlist: upstream AI service error."` | OpenAI API threw a runtime error (auth, quota, outage) after all retries. |
| `"An unexpected error occurred while generating the playlist."` | Unhandled exception — check server logs. |

---

## Caching

Playlist responses are cached in Redis using the exact mood string as the cache key.

- **Cache hit** → instant response; `cached: true`; `X-Cache: HIT` header.
- **Cache miss** → OpenAI is called; result stored; `cached: false`; `X-Cache: MISS` header.
- If Redis is unavailable, the API degrades gracefully — every request goes to OpenAI with no caching.

**Check whether a response was cached:**

```bash
curl -sI -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"mood": "lazy Sunday morning"}' | grep X-Cache
# X-Cache: MISS  (first call)

curl -sI -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"mood": "lazy Sunday morning"}' | grep X-Cache
# X-Cache: HIT   (subsequent call)
```

---

## Rate Limiting

**There is no built-in rate limiting in this version.**

For production deployments, apply rate limiting at the infrastructure level:

- **nginx** — [`limit_req_zone` / `limit_req`](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- **API Gateway** (AWS, GCP, Azure) — configure per-IP or per-key throttling policies
- **Cloudflare** — rate limiting rules in the dashboard

Recommended production limits (starting point):
- **Per IP:** 10 requests/minute for `/api/generate`
- **Global:** scale based on your OpenAI tier quota

Redis caching already reduces upstream OpenAI API calls for repeated moods, which helps manage costs and throughput.

---

## OpenAPI Schema

The live API exposes its full OpenAPI 3.1 schema at:

- **Swagger UI** — [`GET /docs`](http://localhost:8000/docs)
- **ReDoc** — [`GET /redoc`](http://localhost:8000/redoc)
- **Raw JSON schema** — [`GET /openapi.json`](http://localhost:8000/openapi.json)

---

## Environment Variables

| Variable         | Required | Default                   | Description                              |
|------------------|----------|---------------------------|------------------------------------------|
| `OPENAI_API_KEY` | ✅ yes   | —                         | OpenAI API key for playlist generation.  |
| `REDIS_URL`      | no       | `redis://localhost:6379`  | Redis connection URL for response cache. |
