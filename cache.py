import hashlib
import json
from typing import Any, Optional

import redis

from app.core.config import settings
from app.core.logger import logger

try:
    from app.core.metrics import CACHE_HITS, CACHE_MISSES
except Exception:  # pragma: no cover - metrics should exist, this keeps cache resilient.
    CACHE_HITS = None
    CACHE_MISSES = None


_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Return a Redis client, or None if Redis is unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
            )
            _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as exc:
            logger.warning(f"Redis unavailable, caching disabled: {exc}")
            _redis_client = None
    return _redis_client


def make_list_key(prefix: str, **params) -> str:
    """Build a deterministic key for a filtered/paginated list."""
    param_text = json.dumps(params, sort_keys=True, default=str)
    fingerprint = hashlib.md5(param_text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:list:{fingerprint}"


def _entity_from_key(key: str) -> str:
    return key.split(":", 1)[0] if key else "unknown"


def _increment_stat(client: redis.Redis, stat: str) -> None:
    try:
        client.incr(f"cache:stats:{stat}")
    except Exception:
        pass


def cache_get(key: str) -> Optional[Any]:
    client = get_redis()
    if not client:
        return None

    entity = _entity_from_key(key)
    try:
        value = client.get(key)
        if value is not None:
            logger.debug(f"Cache HIT: {key}")
            _increment_stat(client, "hits")
            if CACHE_HITS:
                CACHE_HITS.labels(entity=entity).inc()
            return json.loads(value)

        logger.debug(f"Cache MISS: {key}")
        _increment_stat(client, "misses")
        if CACHE_MISSES:
            CACHE_MISSES.labels(entity=entity).inc()
        return None
    except Exception as exc:
        logger.warning(f"Cache GET error for key '{key}': {exc}")
        return None


def cache_set(key: str, value: Any, ttl: int = settings.CACHE_TTL) -> bool:
    client = get_redis()
    if not client:
        return False

    try:
        client.setex(key, ttl, json.dumps(value, default=str))
        logger.debug(f"Cache SET: {key} (ttl={ttl}s)")
        return True
    except Exception as exc:
        logger.warning(f"Cache SET error for key '{key}': {exc}")
        return False


def cache_get_or_set(key: str, fetch_fn, ttl: int = settings.CACHE_TTL) -> Any:
    cached = cache_get(key)
    if cached is not None:
        return cached

    value = fetch_fn()
    if value is not None:
        cache_set(key, value, ttl)
    return value


def cache_delete(key: str) -> bool:
    client = get_redis()
    if not client:
        return False

    try:
        client.delete(key)
        logger.debug(f"Cache DELETE: {key}")
        return True
    except Exception as exc:
        logger.warning(f"Cache DELETE error for key '{key}': {exc}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern without blocking Redis."""
    client = get_redis()
    if not client:
        return 0

    try:
        deleted = 0
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                client.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        if deleted:
            logger.debug(f"Cache invalidated {deleted} key(s) matching '{pattern}'")
        return deleted
    except Exception as exc:
        logger.warning(f"Cache pattern delete error for '{pattern}': {exc}")
        return 0


def get_cache_stats() -> dict:
    client = get_redis()
    if not client:
        return {
            "available": False,
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "hit_rate_percent": 0.0,
            "memory_used": "N/A",
            "key_counts": {"books": 0, "users": 0, "borrows": 0, "blacklist": 0},
        }

    try:
        hits = int(client.get("cache:stats:hits") or 0)
        misses = int(client.get("cache:stats:misses") or 0)
        total = hits + misses
        memory = client.info("memory").get("used_memory_human", "N/A")

        return {
            "available": True,
            "hits": hits,
            "misses": misses,
            "total_requests": total,
            "hit_rate_percent": round((hits / total) * 100, 2) if total else 0.0,
            "memory_used": memory,
            "key_counts": {
                "books": len(client.keys("books:*")),
                "users": len(client.keys("users:*")),
                "borrows": len(client.keys("borrows:*")),
                "blacklist": len(client.keys("blacklist:*")),
            },
        }
    except Exception as exc:
        logger.warning(f"Cache stats error: {exc}")
        return {"available": False, "error": str(exc)}


def flush_cache(pattern: str = "*") -> int:
    client = get_redis()
    if not client:
        return 0

    if pattern == "*":
        try:
            client.flushdb()
            logger.warning("Redis cache flushed")
            return -1
        except Exception as exc:
            logger.error(f"Cache flush failed: {exc}")
            return 0

    return cache_delete_pattern(pattern)


def check_redis_connection() -> bool:
    client = get_redis()
    if not client:
        return False
    try:
        client.ping()
        return True
    except Exception:
        return False
