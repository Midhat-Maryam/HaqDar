"""
Lightweight security helpers for the FastAPI backend:

- API-key check (optional; enabled only if BACKEND_API_KEY is set)
- Per-IP in-memory rate limiting (fixed window)

Neither of these needs an external service, so the backend stays trivial to
deploy (single container, no Redis dependency) while still not being wide
open. If this backend is ever scaled to multiple worker processes/replicas,
swap the in-memory rate limiter for a shared store (Redis) since counts
won't be consistent across processes otherwise — noted below at the class.
"""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Header, HTTPException, Request, status

from config import (
    BACKEND_API_KEY,
    BACKEND_AUTH_ENABLED,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    """FastAPI dependency: enforce X-API-Key header if BACKEND_API_KEY is
    configured. No-op in local/dev setups where it's left unset."""
    if not BACKEND_AUTH_ENABLED:
        return
    if x_api_key != BACKEND_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


class _InMemoryRateLimiter:
    """Fixed-window rate limiter keyed by client IP.

    NOTE: state lives in process memory, so this only limits correctly when
    the backend runs as a single process/worker. Fine for the default
    `uvicorn` single-worker deployment this project ships with; if you scale
    to multiple workers or replicas, move this to Redis (e.g. via slowapi's
    Redis backend) so all workers share one counter.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def check(self, client_id: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[client_id]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True


_limiter = _InMemoryRateLimiter(RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)


async def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency: reject requests once a client IP exceeds the
    configured rate in the current window."""
    client_id = request.client.host if request.client else "unknown"
    if not _limiter.check(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down and try again shortly.",
        )
