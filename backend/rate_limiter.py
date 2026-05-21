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

    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
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
                        f"Too many requests. You may send up to {self.max_requests} "
                        f"messages per {self.window} seconds. Please wait a moment."
                    ),
                )
            self._buckets[key].append(now)

    def reset(self, key: str) -> None:
        """Clear the bucket for a key (useful in tests)."""
        with self._lock:
            self._buckets.pop(key, None)


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
