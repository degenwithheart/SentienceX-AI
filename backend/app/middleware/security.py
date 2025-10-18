import time
import logging
from typing import Optional

from app.config import get_settings
try:
    from prometheus_client import Counter
    _HAS_PROM = True
except Exception:
    Counter = None
    _HAS_PROM = False

try:
    import redis
    _HAS_REDIS = True
except Exception:
    redis = None
    _HAS_REDIS = False

# Global reference to an in-memory limiter instance (if created)
_INMEM_LIMITER = None

logger = logging.getLogger(__name__)


class SimpleRateLimiter:
    def __init__(self, requests: int = 60, window: int = 60):
        self.requests = requests
        self.window = window
        self.storage = {}  # ip -> [timestamps]

    def allow(self, key: str) -> bool:
        now = int(time.time())
        arr = self.storage.get(key, [])
        # drop old timestamps
        arr = [ts for ts in arr if ts > now - self.window]
        if len(arr) >= self.requests:
            self.storage[key] = arr
            return False
        arr.append(now)
        self.storage[key] = arr
        return True


class TokenBucketInMemory:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = {}
        self.timestamps = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        tokens = self.tokens.get(key, self.capacity)
        last = self.timestamps.get(key, now)
        # refill
        tokens = min(self.capacity, tokens + (now - last) * self.rate)
        if tokens < 1.0:
            self.tokens[key] = tokens
            self.timestamps[key] = now
            return False
        tokens -= 1.0
        self.tokens[key] = tokens
        self.timestamps[key] = now
        return True


def get_inmemory_stats():
    """Return a snapshot of in-memory token-bucket limiter stats.
    Returns a dict mapping keys to {'tokens': <float>, 'last_ts': <float>} or empty if not used.
    """
    # If we used TokenBucketInMemory somewhere, gather stats. We keep no global registry by default,
    # but the TokenBucketInMemory stores tokens/timestamps in instance vars; we can expose them if a global
    # instance is used. For now, return empty placeholder. If your deployment uses the in-memory limiter,
    # you can modify get_limiter() to register the instance in a module-level variable.
    return {"note": "in-memory stats not enabled; register limiter instance in get_limiter() to expose stats"}


def _init_redis_client(redis_url: str):
    # Use redis.from_url which supports rediss:// if redis-py built with TLS
    try:
        client = redis.from_url(redis_url, decode_responses=False)
        # quick ping to validate
        client.ping()
        return client
    except Exception:
        logger.exception("Failed to initialize Redis client for rate limiting")
        return None


def get_limiter(settings=None):
    settings = settings or get_settings()
    redis_url = settings.REDIS_URL
    if redis_url and _HAS_REDIS:
        client = _init_redis_client(redis_url)
        if client:
            # Build a small limiter wrapper object that holds the client and settings
            return {"type": "redis", "client": client, "namespace": settings.RATE_LIMIT_NAMESPACE, "settings": settings}
    # fallback to in-memory limiter
    # use token-bucket in-memory with burst equal to requests
    rate = settings.RATE_LIMIT_REQUESTS / max(1, settings.RATE_LIMIT_WINDOW)
    inst = TokenBucketInMemory(rate=rate, capacity=float(settings.RATE_LIMIT_REQUESTS))
    global _INMEM_LIMITER
    _INMEM_LIMITER = inst
    return inst


def security_middleware(app):
    settings = get_settings()
    limiter = get_limiter(settings=settings)
    # parse per-route overrides from settings.RATE_LIMITS (JSON)
    route_limits = {}
    try:
        import json

        if settings.RATE_LIMITS:
            route_limits = json.loads(settings.RATE_LIMITS)
    except Exception:
        logger.exception("Failed to parse RATE_LIMITS; ignoring per-route limits")

    # Prometheus metric counters
    prom_allowed = None
    prom_blocked = None
    if _HAS_PROM and settings.ENABLE_METRICS:
        prom_allowed = Counter("sentiencex_rate_limit_allowed", "Allowed requests by route", ["route"])
        prom_blocked = Counter("sentiencex_rate_limit_blocked", "Blocked requests by route", ["route"])

    async def middleware(request, call_next):
        response = None
        try:
            client_ip = request.client.host if request.client else "unknown"
            allowed = True

            # Determine per-route limits
            path = request.url.path if hasattr(request, "url") else "/"
            matched = None
            matched_prefix = ""
            # support two kinds of entries in route_limits:
            # 1) plain prefix -> cfg (string key)
            # 2) regex entries where cfg contains {"regex": true, "pattern": "...", ...}
            import re

            for prefix, cfg in route_limits.items():
                # if cfg declares regex, attempt a regex match
                try:
                    if isinstance(cfg, dict) and cfg.get("regex"):
                        pattern = cfg.get("pattern")
                        if not pattern:
                            continue
                        if re.match(pattern, path):
                            # prefer longest regex pattern as heuristic
                            if len(pattern) > len(matched_prefix):
                                matched = cfg
                                matched_prefix = pattern
                    else:
                        # string prefix match, prefer longest prefix
                        if path.startswith(prefix) and len(prefix) > len(matched_prefix):
                            matched = cfg
                            matched_prefix = prefix
                except Exception:
                    logger.exception("Error while evaluating route_limits entry for prefix %s", prefix)
            if matched:
                r_requests = int(matched.get("requests", settings.RATE_LIMIT_REQUESTS))
                r_window = int(matched.get("window", settings.RATE_LIMIT_WINDOW))
                r_burst = int(matched.get("burst", r_requests))
            else:
                r_requests = settings.RATE_LIMIT_REQUESTS
                r_window = settings.RATE_LIMIT_WINDOW
                r_burst = settings.RATE_LIMIT_REQUESTS

            if isinstance(limiter, TokenBucketInMemory):
                allowed = limiter.allow(client_ip)
            elif isinstance(limiter, dict) and limiter.get("type") == "redis":
                # Redis token bucket implemented via Lua for atomicity
                client = limiter["client"]
                ns = limiter.get("namespace", "rl")
                key = f"{ns}:{path}:{client_ip}"
                # token bucket params
                capacity = r_burst
                refill_rate = float(r_requests) / max(1, r_window)
                # Lua script: ARGV[1]=capacity, ARGV[2]=refill_rate, ARGV[3]=now, ARGV[4]=consume
                lua = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local consume = tonumber(ARGV[4])
local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1]) or capacity
local ts = tonumber(data[2]) or now
local delta = math.max(0, now - ts)
tokens = math.min(capacity, tokens + delta * refill)
local allowed = 0
if tokens >= consume then
    tokens = tokens - consume
    allowed = 1
end
redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, math.max(1, math.floor((capacity / refill) * 2)))
return allowed
"""
                try:
                    now_s = time.time()
                    allowed = client.eval(lua, 1, key, str(capacity), str(refill_rate), str(now_s), "1")
                    allowed = bool(int(allowed))
                except Exception:
                    logger.exception("Redis token-bucket eval failed; allowing request")
                    allowed = True
            else:
                # fallback generic behavior
                allowed = True

            if not allowed:
                if prom_blocked is not None:
                    try:
                        prom_blocked.labels(route=matched_prefix or path).inc()
                    except Exception:
                        pass
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

            # increment allowed metric
            if prom_allowed is not None:
                try:
                    prom_allowed.labels(route=matched_prefix or path).inc()
                except Exception:
                    pass

            response = await call_next(request)
            # add security headers
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            return response
        except Exception:
            logger.exception("Security middleware failure")
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=500, content={"detail": "Security middleware error"})

    return middleware
