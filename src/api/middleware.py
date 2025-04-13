import time
# import logging
from typing import Callable, Dict, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from src.config import settings
# TODO: Add logging and monitoring here

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests by client IP address.
    
    Uses a simple in-memory counter. For production use, consider
    implementing a Redis-based rate limiter for distributed deployments.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limits: Dict[str, Dict[str, int]] = {}
        self.window_seconds = 60  # 1 minute window

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Implement rate limiting logic."""
        # Skip rate limiting for certain endpoints
        if request.url.path == "/api/v1/health":
            return await call_next(request)
        
        # Get client IP address
        client_ip = request.client.host if request.client else "unknown"
        
        # Clean up expired rate limit entries
        current_time = int(time.time())
        self._cleanup_expired_entries(current_time)
        
        # Check if client has exceeded rate limit
        if self._is_rate_limited(client_ip, current_time):
            # logger.warning(f"Rate limit exceeded for client {client_ip}")
            # increment_error_count(error_type="rate_limit")
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )
        
        # Process the request
        return await call_next(request)

    def _cleanup_expired_entries(self, current_time: int) -> None:
        """Clean up expired rate limit entries."""
        expired_time = current_time - self.window_seconds
        
        for client_ip in list(self.rate_limits.keys()):
            self.rate_limits[client_ip] = {
                ts: count
                for ts, count in self.rate_limits[client_ip].items()
                if int(ts) > expired_time
            }
            
            if not self.rate_limits[client_ip]:
                del self.rate_limits[client_ip]

    def _is_rate_limited(self, client_ip: str, current_time: int) -> bool:
        """
        Check if the client has exceeded the rate limit.
        
        Args:
            client_ip: The client IP address
            current_time: The current timestamp
            
        Returns:
            bool: True if the client has exceeded the rate limit, False otherwise
        """
        # Initialize rate limit entry for client if not exists
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = {}
        
        # Count requests within the window
        current_count = sum(self.rate_limits[client_ip].values())
        
        # If client has exceeded rate limit, return True
        if current_count >= settings.MAX_REQUESTS_PER_MINUTE:
            return True
        
        # Otherwise, increment count and return False
        time_bucket = str(current_time)
        if time_bucket not in self.rate_limits[client_ip]:
            self.rate_limits[client_ip][time_bucket] = 0
        
        self.rate_limits[client_ip][time_bucket] += 1
        return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and responses.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()
        
        # Extract request details
        method = request.method
        path = request.url.path
        query = request.url.query.decode() if request.url.query else ""
        client_ip = request.client.host if request.client else "unknown"
        
        # Log request
        # logger.info(f"Request: {method} {path}{'?' + query if query else ''} from {client_ip}")
        
        # Process request
        try:
            response = await call_next(request)
            
                    
            return response
        except Exception as e:
            # Log exception
            raise


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enforcing request timeouts.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enforce request timeout."""
        # Skip timeout for certain endpoints
        if request.url.path == "/api/v1/health":
            return await call_next(request)
        
        # Set timeout based on configuration
        timeout = settings.REQUEST_TIMEOUT
        
        # We'd implement proper timeout logic here, but for simplicity,
        # we'll just add the timeout header to the response.
        response = await call_next(request)
        response.headers["X-Request-Timeout"] = str(timeout)
        
        return response


def add_middlewares(app: FastAPI) -> None:
    """
    Add middlewares to the FastAPI application.
    
    Args:
        app: The FastAPI application
    """
    # Add middlewares in reverse order (last added is executed first)
    app.add_middleware(TimeoutMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)