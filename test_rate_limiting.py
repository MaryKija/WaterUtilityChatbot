import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.rate_limiter import RateLimitMiddleware, InMemoryRateLimiter


def test_rate_limit_middleware_chat_and_admin():
    """Verify RateLimitMiddleware properly enforces chat, admin, static, and webhook rules."""
    app = FastAPI()

    @app.get("/chat")
    def chat_route():
        return "chat ok"

    @app.get("/admin/complaints")
    def admin_route():
        return "admin ok"

    @app.get("/static/app.js")
    def static_route():
        return "js ok"

    @app.post("/whatsapp/webhook")
    def webhook_route():
        return "webhook ok"

    # Create low-limit rate limiters specifically for testing
    # Chat: 2 requests per 10 seconds
    chat_limiter = InMemoryRateLimiter(max_requests=2, window_seconds=10, action_name="requests")
    # Admin: 1 request per 10 seconds
    admin_limiter = InMemoryRateLimiter(max_requests=1, window_seconds=10, action_name="admin actions")

    # Add RateLimitMiddleware using these test limiters
    app.add_middleware(
        RateLimitMiddleware,
        chat_limiter=chat_limiter,
        admin_limiter=admin_limiter
    )

    client = TestClient(app)

    # 1. Chat rate limiting
    # First request: Allowed
    response = client.get("/chat")
    assert response.status_code == 200
    assert response.json() == "chat ok"

    # Second request: Allowed
    response = client.get("/chat")
    assert response.status_code == 200

    # Third request: Blocked (429)
    response = client.get("/chat")
    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]
    assert "requests" in response.json()["detail"]

    # 2. Admin rate limiting
    # First request: Allowed
    response = client.get("/admin/complaints")
    assert response.status_code == 200
    assert response.json() == "admin ok"

    # Second request: Blocked (429)
    response = client.get("/admin/complaints")
    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]
    assert "admin actions" in response.json()["detail"]

    # 3. Webhook bypass (Meta webhook should never be rate limited per-IP by the middleware)
    for _ in range(5):
        response = client.post("/whatsapp/webhook")
        assert response.status_code == 200
        assert response.json() == "webhook ok"

    # 4. Static asset bypass (static assets should never be rate limited)
    for _ in range(5):
        response = client.get("/static/app.js")
        assert response.status_code == 200
        assert response.json() == "js ok"
