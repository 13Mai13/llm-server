from fastapi import APIRouter, Request, HTTPException
from src.monitoring.metrics import get_metrics, increment_request_count, increment_error_count
from src.monitoring.logger import get_request_logger
from src.api.routers import api_router


@api_router.get(
    "/metrics",
    summary="Metrics endpoint",
    description="Get all metrics from the metrics store",
)
async def get_metrics_endpoint(fastapi_request: Request):
    """
    Get all metrics from the metrics store.
    Requires API key authentication.
    """
    request_id = fastapi_request.headers.get("X-Request-ID", "unknown")
    logger = get_request_logger(request_id)
    
    try:
        logger.info("Metrics requested")
        metrics = get_metrics()
        increment_request_count(method="GET", path="/metrics", status_code=200)
        return metrics
    except Exception as e:
        error_type = type(e).__name__
        logger.error(
            "Failed to retrieve metrics",
            exc_info=True,
            extra={"error_type": error_type},
        )
        increment_error_count(error_type)
        increment_request_count(method="GET", path="/metrics", status_code=500)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics: {str(e)}"
        ) 