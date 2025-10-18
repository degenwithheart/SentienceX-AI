from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from app.config import get_settings
from app.auth import get_admin_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_redis_client():
    settings = get_settings()
    try:
        import redis
        if settings.REDIS_URL:
            client = redis.from_url(settings.REDIS_URL)
            client.ping()
            return client
    except Exception:
        logger.exception("Failed to connect to Redis for ratelimit admin")
    return None


@router.get("/keys", dependencies=[Depends(get_admin_user)])
def list_keys(pattern: Optional[str] = Query(None, description="glob-style pattern to filter keys")):
    """List rate limit keys in Redis (namespaced). Returns up to 100 keys by default."""
    client = _get_redis_client()
    if not client:
        return {"error": "Redis unavailable"}
    ns = get_settings().RATE_LIMIT_NAMESPACE
    pat = f"{ns}:*" if not pattern else pattern
    try:
        keys = client.keys(pat)
        # limit response size
        keys = keys[:100]
        return {"keys": keys}
    except Exception:
        logger.exception("Error listing rate-limit keys")
        return {"error": "failed to list keys"}


@router.delete("/flush", dependencies=[Depends(get_admin_user)])
def flush_keys(pattern: Optional[str] = Query(None, description="glob-style pattern to delete")):
    """Delete matching rate-limit keys. Use with caution."""
    client = _get_redis_client()
    if not client:
        return {"error": "Redis unavailable"}
    ns = get_settings().RATE_LIMIT_NAMESPACE
    pat = f"{ns}:*" if not pattern else pattern
    try:
        keys = client.keys(pat)
        if not keys:
            return {"deleted": 0}
        deleted = client.delete(*keys)
        return {"deleted": deleted}
    except Exception:
        logger.exception("Error flushing rate-limit keys")
        return {"error": "failed to flush keys"}


@router.get("/stats", dependencies=[Depends(get_admin_user)])
def in_memory_stats():
    """Return stats for the in-memory token-bucket limiter (if used)."""
    try:
        from app.middleware.security import get_inmemory_stats

        return get_inmemory_stats()
    except Exception:
        logger.exception("Failed to retrieve in-memory stats")
        return {"error": "failed to retrieve stats"}
