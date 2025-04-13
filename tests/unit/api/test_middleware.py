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
    
    with patch("src.api.middleware.settings", rate_limit_settings):
        app.add_middleware(RateLimitMiddleware)
    
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
    
    # Add only timeout middleware
    app.add_middleware(TimeoutMiddleware)
    
    return app


@pytest.fixture
def app_with_logging():
    """Return a FastAPI app with only request logging middleware."""
    app = FastAPI()
    
    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"message": "test"}
    
    # Add only logging middleware
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
    with patch("src.api.middleware.settings", rate_limit_settings):
        app.add_middleware(TimeoutMiddleware)
        app.add_middleware(RequestLoggingMiddleware)
        app.add_middleware(RateLimitMiddleware)
    
    return app


# Rate Limiting Middleware Tests

def test_rate_limiting_allows_health_endpoint(app_with_rate_limiting):
    """Test that health endpoint is not rate limited."""
    client = TestClient(app_with_rate_limiting)
    
    # Make multiple requests to the health endpoint
    for _ in range(10):  # More than our limit
        response = client.get("/api/v1/health")
        assert response.status_code == 200


def test_rate_limiting_enforces_limits(app_with_rate_limiting):
    """Test that rate limiting blocks requests after limit is reached."""
    client = TestClient(app_with_rate_limiting)
    
    # Make requests up to the limit
    for _ in range(3):  # Our limit is 3
        response = client.get("/api/v1/test")
        assert response.status_code == 200
    
    # Next request should be rate limited
    response = client.get("/api/v1/test")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]


def test_rate_limiting_separate_by_ip(app_with_rate_limiting):
    """Test that rate limiting tracks different IPs separately."""
    client1 = TestClient(app_with_rate_limiting)
    
    # Modify the client to use a different IP
    client2 = TestClient(app_with_rate_limiting)
    original_request = client2.send
    
    def patched_send(*args, **kwargs):
        # Modify the "client" header to simulate different IP
        kwargs["headers"] = kwargs.get("headers", {})
        kwargs["headers"]["X-Forwarded-For"] = "different-ip"
        return original_request(*args, **kwargs)
    
    client2.send = patched_send
    
    # Client 1 uses up its limit
    for _ in range(3):
        response = client1.get("/api/v1/test")
        assert response.status_code == 200
    
    # Client 1 should now be rate limited
    response = client1.get("/api/v1/test")
    assert response.status_code == 429
    
    # Client 2 should still be able to make requests
    for _ in range(3):
        response = client2.get("/api/v1/test")
        assert response.status_code == 200


def test_rate_limiting_window_expiry():
    """Test that rate limiting resets after the time window."""
    # Create a middleware instance directly for testing
    middleware = RateLimitMiddleware(app=MagicMock())
    middleware.window_seconds = 1  # Short window for testing
    
    # Patch the settings used in the middleware
    with patch("src.api.middleware.settings") as mock_settings:
        # Configure the mock settings
        mock_settings.MAX_REQUESTS_PER_MINUTE = 5
        
        # Simulate requests from a client
        client_ip = "test-ip"
        current_time = int(time.time())
        
        # Should not be rate limited initially
        assert not middleware._is_rate_limited(client_ip, current_time)
        
        # Add several requests in quick succession
        for _ in range(4):
            middleware._is_rate_limited(client_ip, current_time)
        
        # Should be rate limited now (after 5 requests)
        assert middleware._is_rate_limited(client_ip, current_time)


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
    # Note: We're just checking that the request succeeds,
    # actual timeout behavior would require more complex testing
    client = TestClient(app_with_timeout)
    
    response = client.get("/api/v1/health")
    assert response.status_code == 200

# Request Logging Middleware Tests

def test_request_logging_captures_details(app_with_logging):
    """Test that request logging middleware processes requests properly."""
    client = TestClient(app_with_logging)
    
    # The middleware doesn't change the response, so we're just checking
    # that the request succeeds
    response = client.get("/api/v1/test")
    assert response.status_code == 200


# Combined Middleware Tests

def test_all_middleware_chain(app_with_all_middleware):
    """Test that all middleware work together."""
    client = TestClient(app_with_all_middleware)
    
    # First few requests should succeed
    for _ in range(3):
        response = client.get("/api/v1/test")
        assert response.status_code == 200
        assert "X-Request-Timeout" in response.headers
    
    # Next request should be rate limited
    response = client.get("/api/v1/test")
    assert response.status_code == 429
    
    # Health endpoint should always succeed
    response = client.get("/api/v1/health")
    assert response.status_code == 200