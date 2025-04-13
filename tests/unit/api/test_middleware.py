import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.middleware import Middleware
from starlette.responses import JSONResponse

from src.api.middleware import (
    RateLimitMiddleware, 
    RequestLoggingMiddleware, 
    TimeoutMiddleware
)
from src.config import Settings


@pytest.fixture
def rate_limit_settings():
    """Return mock settings with low rate limits for testing."""
    settings = MagicMock()
    settings.API_KEY = "test-api-key"
    settings.LOCAL_MODE = False
    settings.DEBUG = True
    settings.MAX_REQUESTS_PER_MINUTE = 3  # Low limit for testing
    settings.REQUEST_TIMEOUT = 0.5
    return settings

@pytest.fixture
def app_with_rate_limiting(rate_limit_settings):
    """Return a FastAPI app with only rate limiting middleware."""
    app = FastAPI()
    
    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}
    
    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"message": "test"}
    
    # Pass the max requests directly when adding middleware
    with patch("src.api.middleware.RateLimitMiddleware", wraps=RateLimitMiddleware):
        app.add_middleware(RateLimitMiddleware, max_requests=3)
    
    return app


@pytest.fixture
def app_with_timeout():
    """Return a FastAPI app with only timeout middleware."""
    app = FastAPI()
    
    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}
    
    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"message": "test"}
    
    app.add_middleware(TimeoutMiddleware)
    
    return app


@pytest.fixture
def app_with_logging():
    """Return a FastAPI app with only request logging middleware."""
    app = FastAPI()
    
    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"message": "test"}
    
    app.add_middleware(RequestLoggingMiddleware)
    
    return app


@pytest.fixture
def app_with_all_middleware(rate_limit_settings):
    """Return a FastAPI app with all middleware."""
    app = FastAPI()
    
    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}
    
    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"message": "test"}
    
    # Add all middleware in correct order
    app.add_middleware(TimeoutMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware, max_requests=3)  # Set max_requests to 3
    
    return app


# Rate Limiting Middleware Tests

def test_rate_limiting_allows_health_endpoint(app_with_rate_limiting):
    """Test that health endpoint is not rate limited."""
    client = TestClient(app_with_rate_limiting)
    
    for _ in range(10):  # More than our limit
        response = client.get("/api/v1/health")
        assert response.status_code == 200


def test_rate_limiting_enforces_limits(app_with_rate_limiting):
    """Test that rate limiting blocks requests after limit is reached."""
    client = TestClient(app_with_rate_limiting)
    
    for _ in range(3):  # Our limit is 3
        response = client.get("/api/v1/test")
        assert response.status_code == 200
    
    response = client.get("/api/v1/test")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]


def test_rate_limiting_separate_by_ip(app_with_rate_limiting):
    """Test that rate limiting tracks different IPs separately."""
    client1 = TestClient(app_with_rate_limiting)
    
    client2 = TestClient(app_with_rate_limiting)
    
    for _ in range(3):
        response = client1.get("/api/v1/test")
        assert response.status_code == 200
    
    response = client1.get("/api/v1/test")
    assert response.status_code == 429
    
    for _ in range(3):
        response = client2.get("/api/v1/test", headers={"X-Forwarded-For": "different-ip"})
        assert response.status_code == 200


def test_rate_limiting_window_expiry():
    """Test that rate limiting resets after the time window."""
    middleware = RateLimitMiddleware(app=MagicMock(), max_requests=5)
    middleware.window_seconds = 1  # Short window for testing

    client_ip = "test-ip"
    current_time = time.time()

    assert not middleware._is_rate_limited(client_ip, current_time)

    assert not middleware._is_rate_limited(client_ip, current_time)
    assert not middleware._is_rate_limited(client_ip, current_time + 0.1)
    assert not middleware._is_rate_limited(client_ip, current_time + 0.2)
    assert not middleware._is_rate_limited(client_ip, current_time + 0.3)

    assert middleware._is_rate_limited(client_ip, current_time + 0.4)

    time.sleep(1.1)

    new_time = time.time()
    assert not middleware._is_rate_limited(client_ip, new_time)



# Timeout Middleware Tests

def test_timeout_middleware_adds_header(app_with_timeout):
    """Test that timeout middleware adds the expected header."""
    client = TestClient(app_with_timeout)
    
    response = client.get("/api/v1/test")
    assert response.status_code == 200
    assert "X-Request-Timeout" in response.headers
    assert float(response.headers["X-Request-Timeout"]) > 0


def test_timeout_middleware_skips_health_endpoint(app_with_timeout):
    """Test that timeout middleware skips the health endpoint."""
    client = TestClient(app_with_timeout)
    response = client.get("/api/v1/health")
    assert response.status_code == 200

# Request Logging Middleware Tests

def test_request_logging_captures_details(app_with_logging):
    """Test that request logging middleware processes requests properly."""
    client = TestClient(app_with_logging)
    response = client.get("/api/v1/test")
    assert response.status_code == 200


# Combined Middleware Tests

def test_all_middleware_chain(app_with_all_middleware):
    """Test that all middleware work together."""
    client = TestClient(app_with_all_middleware)
    
    for _ in range(3):
        response = client.get("/api/v1/test")
        assert response.status_code == 200
        assert "X-Request-Timeout" in response.headers
    
    response = client.get("/api/v1/test")
    assert response.status_code == 429
    
    response = client.get("/api/v1/health")
    assert response.status_code == 200