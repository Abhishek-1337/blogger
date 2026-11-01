"""Tiered rate limiting: per-user (or per-IP) plus a global ceiling.

Limits are fixed-window counters stored in Redis so every API process
shares one budget. Redis DB 2 is used by default to keep limiter keys
away from the Celery broker (DB 0) and result backend (DB 1).

All limits are configurable through environment variables; see
``.env.example``. Set ``RATE_LIMIT_ENABLED=false`` to disable the
limiter entirely (kill switch).

Failure mode: if the limiter backend is unreachable the limiter fails
open (requests are allowed, a warning is logged). Generation is still
protected in that case because enqueueing itself needs the same Redis.
Set ``RATE_LIMIT_FAIL_CLOSED=true`` to reject generation/login with
503 instead while the limiter backend is down.
"""

import logging
import math
import os
import time
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from fastapi import Depends, HTTPException, Request, Response

from src.auth import get_admin_user, get_current_user
from src.models import User

logger = logging.getLogger(__name__)

_TRUE = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Check:
    key: str
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after_seconds: int = 0
    remaining: int = 0
    limit: int = 0


class InMemoryStore:
    """Single-process store. For tests and single-instance dev only."""

    def __init__(self, time_func=time.monotonic):
        self._time = time_func
        self._counters: dict[str, tuple[int, float]] = {}

    async def check_and_hit(self, checks: list[Check]) -> Decision:
        now = self._time()
        live: dict[str, tuple[int, float]] = {}
        for check in checks:
            count, expires_at = self._counters.get(check.key, (0, now + check.window_seconds))
            if now >= expires_at:
                count, expires_at = 0, now + check.window_seconds
            live[check.key] = (count, expires_at)
        for check in checks:
            count, expires_at = live[check.key]
            if count >= check.limit:
                return Decision(
                    allowed=False,
                    retry_after_seconds=max(1, math.ceil(expires_at - now)),
                    remaining=0,
                    limit=check.limit,
                )
        remaining, limit = None, 0
        for check in checks:
            count, expires_at = live[check.key]
            count += 1
            self._counters[check.key] = (count, expires_at)
            left = check.limit - count
            if remaining is None or left < remaining:
                remaining, limit = left, check.limit
        return Decision(allowed=True, remaining=remaining or 0, limit=limit)


_LUA = """
local retry = 0
for i = 1, #KEYS do
  local limit = tonumber(ARGV[(i - 1) * 2 + 1])
  local count = tonumber(redis.call('GET', KEYS[i]) or '0')
  if count >= limit then
    local ttl = redis.call('TTL', KEYS[i])
    if ttl < 0 then ttl = tonumber(ARGV[(i - 1) * 2 + 2]) end
    if ttl > retry then retry = ttl end
  end
end
if retry > 0 then
  return {0, retry, 0, 0}
end
local remaining = nil
local tight_limit = 0
for i = 1, #KEYS do
  local limit = tonumber(ARGV[(i - 1) * 2 + 1])
  local window = tonumber(ARGV[(i - 1) * 2 + 2])
  local count = redis.call('INCR', KEYS[i])
  if count == 1 then
    redis.call('EXPIRE', KEYS[i], window)
  end
  local left = limit - count
  if remaining == nil or left < remaining then
    remaining = left
    tight_limit = limit
  end
end
return {1, 0, remaining, tight_limit}
"""


class RedisStore:
    def __init__(self, client):
        self._client = client

    async def check_and_hit(self, checks: list[Check]) -> Decision:
        args: list = []
        for check in checks:
            args.extend([check.limit, check.window_seconds])
        allowed, retry, remaining, limit = await self._client.eval(
            _LUA, len(checks), *[c.key for c in checks], *args
        )
        return Decision(
            allowed=bool(allowed),
            retry_after_seconds=int(retry),
            remaining=int(remaining),
            limit=int(limit),
        )


_store_override = None
_redis_client = None


def set_store_override(store) -> None:
    """Replace the limiter backend (used by tests). ``None`` restores Redis."""
    global _store_override
    _store_override = store


def _default_redis_url() -> str:
    url = os.getenv("RATE_LIMIT_REDIS_URL", "").strip()
    if url:
        return url
    base = os.getenv("CELERY_BROKER_URL", "").strip() or "redis://localhost:6379/0"
    parts = urlsplit(base)
    if parts.scheme in ("redis", "rediss"):
        return urlunsplit(parts._replace(path="/2"))
    return "redis://localhost:6379/2"


def _get_store():
    if _store_override is not None:
        return _store_override
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis

        _redis_client = aioredis.from_url(
            _default_redis_url(),
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            decode_responses=True,
        )
    return RedisStore(_redis_client)


def _enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() in _TRUE


def _fail_closed() -> bool:
    return os.getenv("RATE_LIMIT_FAIL_CLOSED", "false").strip().lower() in _TRUE


def _limit(env_name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(env_name, "") or default))
    except ValueError:
        return default


def _rules(prefix: str, defaults: list[tuple[str, int, int]]) -> list[Check]:
    rules = []
    for suffix, default, window in defaults:
        limit = _limit(f"RATE_LIMIT_{prefix}_{suffix}", default)
        if limit > 0:
            rules.append(Check(key="", limit=limit, window_seconds=window))
    return rules


def _scoped(rules: list[Check], scope: str, identifier: str) -> list[Check]:
    return [
        Check(
            key=f"ratelimit:{scope}:{identifier}:{rule.window_seconds}",
            limit=rule.limit,
            window_seconds=rule.window_seconds,
        )
        for rule in rules
    ]


async def _enforce(tier: str, checks: list[Check], fail_closed_tier: bool = False):
    if not _enabled() or not checks:
        return None
    try:
        decision = await _get_store().check_and_hit(checks)
    except Exception:
        logger.warning("rate limiter backend unavailable; failing open", exc_info=True)
        if fail_closed_tier and _fail_closed():
            raise HTTPException(status_code=503, detail="Rate limiter unavailable.")
        return None
    if decision.allowed:
        return decision
    raise HTTPException(
        status_code=429,
        detail=(
            f"Rate limit exceeded for {tier}. "
            f"Try again in {decision.retry_after_seconds} seconds."
        ),
        headers={
            "Retry-After": str(decision.retry_after_seconds),
            "X-RateLimit-Limit": str(decision.limit),
            "X-RateLimit-Remaining": "0",
        },
    )


def _set_headers(response: Response, decision) -> None:
    if decision is None:
        return
    response.headers["X-RateLimit-Limit"] = str(decision.limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)


# --- FastAPI dependencies, one per cost tier -------------------------------


async def limit_generation(
    response: Response, user: User = Depends(get_current_user)
) -> None:
    user_rules = _rules("GEN_PER_USER", [("PER_MINUTE", 10, 60), ("PER_DAY", 100, 86400)])
    global_rules = _rules("GEN_GLOBAL", [("PER_MINUTE", 100, 60)])
    checks = _scoped(user_rules, "gen:user", str(user.id)) + _scoped(
        global_rules, "gen:global", "all"
    )
    _set_headers(
        response, await _enforce("blog generation", checks, fail_closed_tier=True)
    )


async def limit_polling(response: Response, user: User = Depends(get_current_user)) -> None:
    user_rules = _rules("POLL_PER_USER", [("PER_MINUTE", 300, 60)])
    global_rules = _rules("POLL_GLOBAL", [("PER_MINUTE", 6000, 60)])
    checks = _scoped(user_rules, "poll:user", str(user.id)) + _scoped(
        global_rules, "poll:global", "all"
    )
    _set_headers(response, await _enforce("task polling", checks))


async def limit_reads(response: Response, user: User = Depends(get_current_user)) -> None:
    user_rules = _rules("READ_PER_USER", [("PER_MINUTE", 300, 60)])
    global_rules = _rules("READ_GLOBAL", [("PER_MINUTE", 6000, 60)])
    checks = _scoped(user_rules, "read:user", str(user.id)) + _scoped(
        global_rules, "read:global", "all"
    )
    _set_headers(response, await _enforce("reads", checks))


async def limit_admin_reads(
    response: Response, user: User = Depends(get_admin_user)
) -> None:
    user_rules = _rules("ADMIN_PER_USER", [("PER_MINUTE", 120, 60)])
    global_rules = _rules("ADMIN_GLOBAL", [("PER_MINUTE", 1200, 60)])
    checks = _scoped(user_rules, "admin:user", str(user.id)) + _scoped(
        global_rules, "admin:global", "all"
    )
    _set_headers(response, await _enforce("admin reads", checks))


async def limit_login(request: Request, response: Response) -> None:
    ip = request.client.host if request.client else "unknown"
    ip_rules = _rules("LOGIN_PER_IP", [("PER_MINUTE", 20, 60)])
    global_rules = _rules("LOGIN_GLOBAL", [("PER_MINUTE", 1000, 60)])
    checks = _scoped(ip_rules, "login:ip", ip) + _scoped(
        global_rules, "login:global", "all"
    )
    _set_headers(
        response, await _enforce("login", checks, fail_closed_tier=True)
    )
