from src.api.routers import api_router
from src.monitoring.logger import get_request_logger
from fastapi import HTTPException, status
from src.llm.providers import get_llm_providers
from src.monitoring.metrics import record_request_metrics
from src.api.models import (
    StructuredCompletionRequest,
    StructuredCompletionResponse,
    ErrorResponse,
    UsageInfo,
)
from src.validation.schema_registry import get_schema_registry
from src.validation.transformers import apply_transformers
from outlines import models, generate
import json
import uuid

logger = get_request_logger()


@api_router.post(
    "/structured-completions",
    response_model=StructuredCompletionResponse,
    summary="Generate structured text completion",
    description="Generate a structured completion using output validation with schemas",
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_structured_completion(
    request: StructuredCompletionRequest,
) -> StructuredCompletionResponse:
    """
    Generate a structured completion using output validation with schemas.
    """
    providers = get_llm_providers()
    schema_registry = get_schema_registry()

    if request.provider not in providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{request.provider}' not supported",
        )

    # Get the schema to use for validation
    if request.schema_id:
        schema = await schema_registry.get_schema(request.schema_id)
        if not schema:
            raise HTTPException(
                status_code=404,
                detail=f"Schema with ID '{request.schema_id}' not found",
            )
    elif request.validation_schema:
        schema = request.validation_schema
    else:
        raise HTTPException(
            status_code=400,
            detail="Either schema_id or validation_schema must be provided",
        )

    try:
        with record_request_metrics(request.provider, request.model, structured=True):
            # Initialize Outlines with the provider's model
            if request.provider == "openai":
                model = models.openai(request.model)
            elif request.provider == "anthropic":
                model = models.anthropic(request.model)
            elif request.provider == "groq":
                model = models.groq(request.model)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Provider '{request.provider}' not supported for structured completions",
                )

            # Create a JSON generator with the schema
            generator = generate.json(
                model,
                schema,
                whitespace_pattern=r"[\n\t ]*",  # Allow whitespace in JSON
                max_tokens=request.max_tokens
                or 1000,  # Use requested max_tokens or default
            )

            # Generate structured output directly
            try:
                structured_output = generator(request.prompt)
            except Exception as e:
                logger.error(f"Error generating structured output: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate structured output: {str(e)}",
                )

            # Apply transformers if provided
            if request.transformers is not None:
                structured_output = await apply_transformers(
                    structured_output, request.transformers
                )

            # Create a response with the structured output
            return StructuredCompletionResponse(
                id=str(uuid.uuid4()),  # Generate a unique ID
                provider=request.provider,
                model=request.model,
                raw_text=json.dumps(structured_output),  # Convert back to JSON string
                structured_output=structured_output,
                usage=UsageInfo(  # TODO: Get actual usage from the model
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                ),
            )

    except Exception as e:
        logger.error(f"Error in structured completion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
