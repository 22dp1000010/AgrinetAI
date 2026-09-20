"""Minimal in-memory sliding-window rate limiter for /api/* endpoints.

Protects the Gemini quota from abuse of the public endpoints. In-memory is
per-instance, which is exactly the granularity Cloud Run scales at; no
external dependency or store needed at this traffic level.
"""

import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

WINDOW_S = 60
MAX_REQUESTS = 60  # per client IP per window, /api/* only (seed script fits)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = MAX_REQUESTS, window_s: int = WINDOW_S):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_s = window_s
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        # Cloud Run puts the real client IP first in X-Forwarded-For.
        forwarded = request.headers.get("x-forwarded-for", "")
        client_ip = forwarded.split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        now = time.time()
        hits = self._hits[client_ip]
        while hits and hits[0] < now - self.window_s:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests — please wait a minute."},
            )
        hits.append(now)
        return await call_next(request)
