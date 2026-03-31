"""
Redis caching module.

Provides an async Redis client initialised from REDIS_URL in settings, plus a
FastAPI dependency ``get_redis()`` that yields a live client.  If Redis is
unavailable (connection error, misconfiguration, etc.) the dependency yields
``None`` so callers can skip caching gracefully without crashing the request.

Usage in a route
----------------
::

    from fastapi import Depends
    from redis.asyncio import Redis
    from cache import get_redis

    @router.get("/example")
    async def example(redis: Redis | None = Depends(get_redis)):
        if redis is not None:
            cached = await redis.get("some-key")
        ...
"""

import logging
import re
import string
from typing import AsyncGenerator

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level client (lazy, singleton)
# ---------------------------------------------------------------------------

_redis_client: Redis | None = None


def _get_client() -> Redis:
    """
    Return the module-level Redis client, creating it on first call.

    The client is created with ``decode_responses=True`` so all values are
    returned as strings rather than bytes.  The client object itself does not
    open a connection until the first command is issued, so construction here
    is cheap and always safe.
    """
    global _redis_client
    if _redis_client is None:
        logger.debug("Initialising async Redis client (url=%s)", settings.REDIS_URL)
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,   # fail fast rather than blocking requests
            socket_timeout=2,
        )
    return _redis_client


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_redis() -> AsyncGenerator[Redis | None, None]:
    """
    FastAPI dependency that yields an active Redis client or ``None``.

    A quick ``PING`` is issued to verify the connection is alive.  If Redis is
    down (or misconfigured), the error is logged at WARNING level and ``None``
    is yielded so the caller can proceed without caching.

    Yields
    ------
    Redis | None
        Live Redis client, or ``None`` when Redis is unreachable.
    """
    client = _get_client()
    try:
        await client.ping()
        yield client
    except RedisError as exc:
        logger.warning(
            "Redis unavailable — caching disabled for this request. "
            "Error: %s: %s",
            type(exc).__name__,
            exc,
        )
        yield None
    except Exception as exc:  # pragma: no cover — safety net for unexpected errors
        logger.warning(
            "Unexpected error connecting to Redis — caching disabled. "
            "Error: %s: %s",
            type(exc).__name__,
            exc,
        )
        yield None


# ---------------------------------------------------------------------------
# Helpers for cache consumers
# ---------------------------------------------------------------------------


async def cache_get(redis: Redis | None, key: str) -> str | None:
    """
    Retrieve a cached value by key.

    Returns ``None`` if the key is absent *or* if ``redis`` is ``None``
    (Redis unavailable).

    Parameters
    ----------
    redis:
        Active Redis client, or ``None`` to skip the cache.
    key:
        Cache key to look up.

    Returns
    -------
    str | None
        Cached string value, or ``None`` on miss / unavailability.
    """
    if redis is None:
        return None
    try:
        value = await redis.get(key)
        if value is not None:
            logger.debug("Cache HIT  key=%r", key)
        else:
            logger.debug("Cache MISS key=%r", key)
        return value
    except RedisError as exc:
        logger.warning("Redis GET failed for key %r: %s: %s", key, type(exc).__name__, exc)
        return None


async def cache_set(
    redis: Redis | None,
    key: str,
    value: str,
    ttl_seconds: int = 3600,
) -> None:
    """
    Store a value in the cache with an optional TTL.

    Silently skips the write when ``redis`` is ``None`` or if a Redis error
    occurs, so failures here never propagate to the caller.

    Parameters
    ----------
    redis:
        Active Redis client, or ``None`` to skip the cache.
    key:
        Cache key.
    value:
        String value to store.
    ttl_seconds:
        Time-to-live in seconds (default 1 hour).
    """
    if redis is None:
        return
    try:
        await redis.set(key, value, ex=ttl_seconds)
        logger.debug("Cache SET  key=%r  ttl=%ds", key, ttl_seconds)
    except RedisError as exc:
        logger.warning("Redis SET failed for key %r: %s: %s", key, type(exc).__name__, exc)


# ---------------------------------------------------------------------------
# Playlist-specific cache helpers
# ---------------------------------------------------------------------------

_CACHE_PREFIX = "playlist:"
_PLAYLIST_TTL = 3600  # 1 hour

# Pre-built translation table to strip ASCII punctuation
_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def normalize_mood(mood: str) -> str:
    """
    Normalise a raw mood string into a stable, deterministic cache-key fragment.

    Steps applied in order:

    1. Strip leading/trailing whitespace.
    2. Collapse internal runs of whitespace to a single space.
    3. Lowercase.
    4. Remove ASCII punctuation.

    Parameters
    ----------
    mood:
        Raw mood string entered by the user.

    Returns
    -------
    str
        Normalised string suitable for use as a cache-key component.
    """
    mood = mood.strip()
    mood = re.sub(r"\s+", " ", mood)
    mood = mood.lower()
    mood = mood.translate(_PUNCT_TABLE)
    return mood


async def get_cached_playlist(
    redis: Redis | None,
    mood: str,
) -> "PlaylistResponse | None":
    """
    Retrieve a cached ``PlaylistResponse`` for the given mood.

    The mood is normalised before lookup so that minor variations in
    capitalisation / punctuation / spacing resolve to the same cache entry.

    Parameters
    ----------
    redis:
        Active Redis client, or ``None`` when Redis is unavailable.
    mood:
        Raw mood string (will be normalised internally).

    Returns
    -------
    PlaylistResponse | None
        Deserialised response if a cache entry exists, otherwise ``None``.
    """
    # Import here to avoid a circular dependency at module load time.
    from models import PlaylistResponse  # noqa: PLC0415

    key = _CACHE_PREFIX + normalize_mood(mood)
    raw = await cache_get(redis, key)
    if raw is None:
        return None
    try:
        return PlaylistResponse.model_validate_json(raw)
    except Exception as exc:  # malformed JSON / schema mismatch — treat as miss
        logger.warning("Failed to deserialise cached playlist for key %r: %s", key, exc)
        return None


async def set_cached_playlist(
    redis: Redis | None,
    mood: str,
    playlist: "PlaylistResponse",
    ttl_seconds: int = _PLAYLIST_TTL,
) -> None:
    """
    Serialise and store a ``PlaylistResponse`` in the cache.

    Parameters
    ----------
    redis:
        Active Redis client, or ``None`` when Redis is unavailable.
    mood:
        Raw mood string (will be normalised to form the cache key).
    playlist:
        The playlist response to cache.
    ttl_seconds:
        Time-to-live in seconds (default 1 hour).
    """
    key = _CACHE_PREFIX + normalize_mood(mood)
    try:
        serialised = playlist.model_dump_json()
    except Exception as exc:
        logger.warning("Failed to serialise playlist for caching (key=%r): %s", key, exc)
        return
    await cache_set(redis, key, serialised, ttl_seconds=ttl_seconds)
