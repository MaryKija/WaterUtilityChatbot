"""backend/rate_limiter.py

In-process rate limiter for the chat endpoint.

Protects the Groq API budget during demos and production use.
Uses a sliding-window counter keyed by client IP (or user_id for
authenticated channels like WhatsApp webhooks).

Configuration via environment variables (read from config):
  RATE_LIMIT_ENABLED   = True / False   (default True)
  RATE_LIMIT_REQUESTS  = int            (default 20 per window)
  RATE_LIMIT_WINDOW    = int seconds    (default 60)
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Sliding-window rate limiter backed by an in-process dict.

    Thread-safe for uvicorn's default single-process mode.
    For multi-worker deployments, swap the dict for a Redis backend.
    """

    def __init__(self, max_requests: int = 20, window_seconds: int = 60, action_name: str = "messages"):
        self.max_requests = max_requests
        self.window = window_seconds
        self.action_name = action_name
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str) -> None:
        """Raise HTTP 429 if the key has exceeded the rate limit."""
        if not key:
            key = "unknown"

        now = time.time()
        with self._lock:
            # Prune timestamps outside the current window
            self._buckets[key] = [
                t for t in self._buckets[key] if now - t < self.window
            ]
            if len(self._buckets[key]) >= self.max_requests:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Too many requests. You may perform up to {self.max_requests} "
                        f"{self.action_name} per {self.window} seconds. Please wait a moment."
                    ),
                )
            self._buckets[key].append(now)

    def reset(self, key: str) -> None:
        """Clear the bucket for a key (useful in tests)."""
        with self._lock:
            self._buckets.pop(key, None)


def get_client_ip(request: Request) -> str:
    """Return the client IP address, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(',')[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware to automatically enforce per-IP rate limits.
    
    Tiers:
      - Chat APIs (/chat, /feedback, etc.): 60 requests/minute (configurable)
      - Admin & Auth APIs (/admin/*, /auth/*): 10 requests/minute (configurable)
    """

    def __init__(self, app, chat_limiter: InMemoryRateLimiter | None = None, admin_limiter: InMemoryRateLimiter | None = None):
        super().__init__(app)
        
        # We can dynamically load limits or use defaults
        chat_req = int(os.getenv("RATE_LIMIT_CHAT_REQUESTS", "60"))
        chat_window = int(os.getenv("RATE_LIMIT_CHAT_WINDOW", "60"))
        admin_req = int(os.getenv("RATE_LIMIT_ADMIN_REQUESTS", "10"))
        admin_window = int(os.getenv("RATE_LIMIT_ADMIN_WINDOW", "60"))

        self.chat_limiter = chat_limiter or InMemoryRateLimiter(
            max_requests=chat_req, 
            window_seconds=chat_window, 
            action_name="requests"
        )
        self.admin_limiter = admin_limiter or InMemoryRateLimiter(
            max_requests=admin_req, 
            window_seconds=admin_window, 
            action_name="admin actions"
        )
        
        self.enabled = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        path = request.url.path

        # 1. Skip static assets, Vite dev server files, and non-API files
        if (
            path.startswith("/assets") or 
            path.startswith("/static") or 
            path.startswith("/admin/assets") or
            any(path.endswith(ext) for ext in [".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".json", ".txt", ".woff", ".woff2", ".ttf", ".map"])
        ):
            return await call_next(request)

        # 2. Skip WhatsApp webhook endpoint for per-IP middleware limiting
        # Meta's webhook servers send multi-user traffic to /whatsapp/webhook.
        # Specific user rate limiting is applied inside the webhook endpoint itself!
        if path == "/whatsapp/webhook":
            return await call_next(request)

        # 3. Determine tier & apply rate limit by IP
        client_ip = get_client_ip(request)
        
        try:
            if path.startswith("/admin/") or path.startswith("/auth/"):
                # Admin and auth endpoints: 10 requests / minute
                key = f"admin:{client_ip}"
                self.admin_limiter.check(key)
            elif (
                path == "/chat" or 
                path == "/chat/clear" or 
                path.startswith("/chat/updates") or 
                path == "/feedback" or 
                path.startswith("/feedback/") or
                path == "/api/chat"
            ):
                # Chat actions: 60 requests / minute
                key = f"chat:{client_ip}"
                self.chat_limiter.check(key)
        except HTTPException as exc:
            # Return standard FastAPI JSON 429 Response
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )

        return await call_next(request)


def _build_limiter() -> InMemoryRateLimiter:
    """Build the singleton limiter from environment / config values."""
    enabled = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    if not enabled:
        # Return a no-op limiter
        class _NoOp(InMemoryRateLimiter):
            def check(self, key: str) -> None:  # type: ignore[override]
                pass
        return _NoOp()

    max_req = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
    window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    return InMemoryRateLimiter(max_requests=max_req, window_seconds=window)


# Singleton — imported by main.py
rate_limiter = _build_limiter()


def get_client_key(request: Request, user_id: str | None = None) -> str:
    """Return the best available identifier for rate-limiting.

    Priority: explicit user_id (WhatsApp / authenticated) > X-Forwarded-For > client IP.
    """
    if user_id and not user_id.startswith("demo-"):
        return f"uid:{user_id}"

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"

    if request.client:
        return f"ip:{request.client.host}"

    return "ip:unknown"
