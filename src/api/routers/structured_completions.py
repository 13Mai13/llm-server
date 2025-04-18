from src.api.routers import api_router
from src.monitoring.logger import get_request_logger
from fastapi import HTTPException, status
from src.llm.providers import get_llm_providers
from src.monitoring.metrics import record_request_metrics
from src.api.models import (
    StructuredCompletionRequest,
    StructuredCompletionResponse,
    ErrorResponse,
)
from src.validation.schema_registry import get_schema_registry
from src.validation.output_validator import validate_output
import json

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

    provider = providers[request.provider]

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
        # Record metrics for the request
        with record_request_metrics(request.provider, request.model, structured=True):
            # Generate text from provider
            response = await provider.generate(
                model=request.model,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                stop=request.stop,
            )

            # Parse the JSON response
            try:
                json.loads(response.text)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Provider returned invalid JSON output",
                )

            # Validate and transform output
            validated_output = await validate_output(
                text=response.text,
                schema=schema,
                transformers=request.transformers,
            )

            return StructuredCompletionResponse(
                id=response.id,
                provider=request.provider,
                model=request.model,
                raw_text=response.text,
                structured_output=validated_output,
                usage=response.usage,
            )
    except Exception as e:
        logger.error(f"Error in structured completion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
