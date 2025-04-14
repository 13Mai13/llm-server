from pydantic import BaseModel, Field
from typing import List


class HealthResponse(BaseModel):
    """Health check response."""

    status: int = Field(..., description="HTTP status code")
    description: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")

class ModelInfo(BaseModel):
    """Information about an LLM model."""
    id: str = Field(..., description="Model identifier")
    provider: str = Field(..., description="Provider name (groq, openai, etc.)")
    name: str = Field(..., description="Human-readable model name")
    context_window: int = Field(..., description="Maximum context window size in tokens")
    supports_structured_output: bool = Field(
        ..., description="Whether the model supports structured output validation"
    )
    max_output_tokens: int = Field(..., description="Maximum output tokens")

class ModelsResponse(BaseModel):
    """Response containing available models."""
    models: List[ModelInfo] = Field(..., description="List of available models")