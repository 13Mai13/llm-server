from api.routers import api_router
from api.models import HealthResponse

@api_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Check if the API is running and get basic health information",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint that returns the status of the service.
    """
    return HealthResponse(status=200, description="ok", version="0.1.0")
