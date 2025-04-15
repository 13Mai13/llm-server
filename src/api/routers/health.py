from fastapi import Request
from src.api.routers import api_router
from src.api.models import HealthResponse
from src.monitoring.metrics import increment_request_count, increment_error_count
from src.monitoring.logger import get_request_logger

logger = get_request_logger()


@api_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Check if the API is running and get basic health information",
)
async def health_check(fastapi_request: Request) -> HealthResponse:
    """
    Health check endpoint that returns the status of the service.
    """
    request_id = fastapi_request.headers.get("X-Request-ID", "unknown")
    logger = get_request_logger(request_id)

    try:
        logger.info("Health check requested")
        increment_request_count(method="GET", path="/health", status_code=200)

        return HealthResponse(status=200, description="ok", version="0.1.0")
    except Exception as e:
        error_type = type(e).__name__
        logger.error(
            "Health check failed",
            exc_info=True,
            extra={"error_type": error_type},
        )
        increment_error_count(error_type)
        increment_request_count(method="GET", path="/health", status_code=500)
        raise
