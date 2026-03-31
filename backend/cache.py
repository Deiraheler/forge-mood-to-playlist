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
