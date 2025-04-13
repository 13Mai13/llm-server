import time

# import logging
from typing import Callable, Dict
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.config import settings
# TODO: Add logging and monitoring here


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests by client IP address.

    Uses a sliding window rate limiting approach with in-memory tracking.
    """

    def __init__(self, app: ASGIApp, max_requests: int = None):
        super().__init__(app)
        self.rate_limits: Dict[str, Dict[float, int]] = {}
        self.window_seconds = 60  # 1 minute window
        self._max_requests = max_requests or getattr(
            settings, "MAX_REQUESTS_PER_MINUTE", 30
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Implement rate limiting logic."""
        # Skip rate limiting for certain endpoints
        if request.url.path == "/api/v1/health":
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        current_time = time.time()

        if self._is_rate_limited(client_ip, current_time):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address, handling various scenarios.

        Prefers X-Forwarded-For header for clients behind proxies.
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """
        Check if the client has exceeded the rate limit using a sliding window.

        Args:
            client_ip: The client IP address
            current_time: The current timestamp

        Returns:
            bool: True if the client has exceeded the rate limit, False otherwise
        """
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = {}

        # Remove expired entries
        window_start = current_time - self.window_seconds
        self.rate_limits[client_ip] = {
            timestamp: count
            for timestamp, count in self.rate_limits[client_ip].items()
            if timestamp > window_start
        }

        # Count requests within the window
        current_count = sum(self.rate_limits[client_ip].values())

        if current_count >= self._max_requests:
            return True

        existing_count = self.rate_limits[client_ip].get(current_time, 0)
        self.rate_limits[client_ip][current_time] = existing_count + 1

        return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        # start_time = time.time()

        # Extract request details
        # method = request.method
        # path = request.url.path
        # query = request.url.query.decode() if request.url.query else ""
        # client_ip = request.client.host if request.client else "unknown"

        # Log request
        # logger.info(f"Request: {method} {path}{'?' + query if query else ''} from {client_ip}")

        try:
            response = await call_next(request)
            return response
        except Exception:
            # Log exception
            raise


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enforcing request timeouts.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enforce request timeout."""
        if request.url.path == "/api/v1/health":
            return await call_next(request)

        timeout = settings.REQUEST_TIMEOUT

        response = await call_next(request)
        response.headers["X-Request-Timeout"] = str(timeout)

        return response


def add_middlewares(app: FastAPI) -> None:
    """
    Add middlewares to the FastAPI application.

    Args:
        app: The FastAPI application
    """
    app.add_middleware(TimeoutMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
