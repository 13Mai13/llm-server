from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


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
    context_window: int = Field(
        ..., description="Maximum context window size in tokens"
    )
    supports_structured_output: bool = Field(
        ..., description="Whether the model supports structured output validation"
    )
    max_output_tokens: int = Field(..., description="Maximum output tokens")


class ModelsResponse(BaseModel):
    """Response containing available models."""

    models: List[ModelInfo] = Field(..., description="List of available models")


class UsageInfo(BaseModel):
    """Usage information for a completion request."""

    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(
        ..., description="Number of tokens in the completion"
    )
    total_tokens: int = Field(..., description="Total number of tokens used")


class CompletionRequest(BaseModel):
    """Request for text completion."""

    provider: str = Field(..., description="LLM provider (openai, anthropic, etc.)")
    model: str = Field(..., description="Model identifier")
    prompt: str = Field(..., description="The prompt to generate completion for")
    max_tokens: Optional[int] = Field(
        None, description="Maximum number of tokens to generate"
    )
    temperature: Optional[float] = Field(
        0.7, ge=0.0, le=1.0, description="Sampling temperature (0.0 to 1.0)"
    )
    top_p: Optional[float] = Field(
        1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter"
    )
    stop: Optional[List[str]] = Field(None, description="Stop sequences")


class CompletionResponse(BaseModel):
    """Response for text completion."""

    id: str = Field(..., description="Unique identifier for this completion")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model identifier used")
    text: str = Field(..., description="Completed text")
    usage: UsageInfo = Field(..., description="Token usage information")


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str = Field(..., description="Error message")


class SchemaDefinition(BaseModel):
    """Definition of a schema for structured output validation."""

    id: Optional[str] = Field(None, description="Schema identifier")
    name: str = Field(..., description="Schema name")
    description: Optional[str] = Field(None, description="Schema description")
    json_schema: Dict[str, Any] = Field(..., description="JSON schema")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class TransformerDefinition(BaseModel):
    """Definition of a transformer for post-processing."""

    name: str = Field(..., description="Transformer name")
    config: Optional[Dict[str, Any]] = Field(
        None, description="Transformer configuration"
    )


class StructuredCompletionRequest(CompletionRequest):
    """Request for structured completion."""

    schema_id: Optional[str] = Field(
        None, description="ID of a registered schema to use for validation"
    )
    validation_schema: Optional[Dict[str, Any]] = Field(
        None, description="Inline schema to use for validation"
    )
    transformers: Optional[List[TransformerDefinition]] = Field(
        None, description="Transformers to apply to the validated output"
    )


class StructuredCompletionResponse(BaseModel):
    """Response for structured completion."""

    id: str = Field(..., description="Unique identifier for this completion")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model identifier used")
    raw_text: str = Field(..., description="Raw completion text before validation")
    structured_output: Dict[str, Any] = Field(
        ..., description="Structured output after validation and transformation"
    )
    usage: UsageInfo = Field(..., description="Token usage information")
