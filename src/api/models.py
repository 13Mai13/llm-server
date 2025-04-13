from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    """Health check response."""
    status: int = Field(..., description="HTTP status code")
    description: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
