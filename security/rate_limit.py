from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from fastapi import Request

try:
    from redis.asyncio import Redis
    from redis.asyncio.client import Redis as RedisClient
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover
    RedisClient = None  # type: ignore
    redis_async = None  # type: ignore


_LUA = r"""
local key = KEYS[1]
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refill_per_sec = tonumber(ARGV[3])

local tokens = tonumber(redis.call("HGET", key, "t"))
local ts = tonumber(redis.call("HGET", key, "ts"))
if tokens == nil then
  tokens = capacity
  ts = now
end

local dt = math.max(0, now - ts)
local refill = dt * refill_per_sec
tokens = math.min(capacity, tokens + refill)

local allowed = 0
if tokens >= 1 then
  allowed = 1
  tokens = tokens - 1
end

redis.call("HSET", key, "t", tokens, "ts", now)
redis.call("EXPIRE", key, math.ceil(capacity / refill_per_sec) + 5)
return allowed
"""


class _LocalLimiter:
    def __init__(self, rpm: int):
        self._rpm = max(1, int(rpm))
        self._capacity = float(self._rpm)
        self._refill = float(self._rpm) / 60.0
        self._state: Dict[str, Tuple[float, float]] = {}  # key -> (tokens, ts)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = time.time()
        async with self._lock:
            tokens, ts = self._state.get(key, (self._capacity, now))
            dt = max(0.0, now - ts)
            tokens = min(self._capacity, tokens + dt * self._refill)
            ok = tokens >= 1.0
            if ok:
                tokens -= 1.0
            self._state[key] = (tokens, now)
            return ok


@dataclass
class RateLimiter:
    enabled: bool
    rpm: int
    redis_url: str

    def __post_init__(self) -> None:
        self._capacity = max(1, int(self.rpm))
        self._refill_per_sec = float(self._capacity) / 60.0
        self._redis: Optional["Redis"] = None
        self._lua_sha: Optional[str] = None
        self._local = _LocalLimiter(rpm=self._capacity)

    async def _get_redis(self) -> Optional["Redis"]:
        if redis_async is None:
            return None
        if self._redis is None:
            try:
                self._redis = redis_async.from_url(self.redis_url, decode_responses=False)
                # Trigger connection early.
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    async def allow(self, request: Request) -> bool:
        if not self.enabled:
            return True
        ip = request.client.host if request.client else "unknown"
        key = f"rl:{ip}"

        r = await self._get_redis()
        if r is None:
            return await self._local.allow(key)

        try:
            if self._lua_sha is None:
                self._lua_sha = await r.script_load(_LUA)
            now = time.time()
            allowed = await r.evalsha(self._lua_sha, 1, key, now, self._capacity, self._refill_per_sec)
            return bool(int(allowed))
        except Exception:
            # Fail closed would be harsh for local single-user; fallback to local limiter.
            return await self._local.allow(key)

