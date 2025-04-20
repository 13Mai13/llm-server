from fastapi import HTTPException, status, Request
from src.api.routers import api_router
from src.llm.providers import get_llm_providers
from src.monitoring.metrics import record_request_metrics, increment_error_count
from src.monitoring.logger import get_request_logger
from src.api.models import (
    CompletionRequest,
    CompletionResponse,
    ErrorResponse,
)

logger = get_request_logger()


@api_router.post(
    "/completions",
    response_model=CompletionResponse,
    summary="Generate text completion",
    description="Generate a text completion from a prompt without structured validation",
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_completion(
    request: CompletionRequest, fastapi_request: Request
) -> CompletionResponse:
    """
    Generate a text completion from a prompt without structured validation.
    """
    request_id = fastapi_request.headers.get("X-Request-ID", "unknown")
    logger = get_request_logger(request_id)

    providers = get_llm_providers()

    if request.provider not in providers:
        error_msg = f"Provider '{request.provider}' not supported"
        logger.warning(error_msg)
        increment_error_count("unsupported_provider")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    provider = providers[request.provider]

    try:
        logger.info(
            f"Generating completion with provider {request.provider} and model {request.model}",
            extra={
                "provider": request.provider,
                "model": request.model,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            },
        )

        # Record initial metrics
        with record_request_metrics(request.provider, request.model) as metrics:
            # Generate the response
            response = await provider.generate(
                model=request.model,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                stop=request.stop,
            )

            # Update metrics with actual token counts
            metrics.update(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

        logger.info(
            f"Successfully generated completion with {response.usage.total_tokens} tokens",
            extra={
                "provider": request.provider,
                "model": request.model,
                "total_tokens": response.usage.total_tokens,
            },
        )

        return CompletionResponse(
            id=response.id,
            provider=request.provider,
            model=request.model,
            text=response.text,
            usage=response.usage,
        )
    except Exception as e:
        error_type = type(e).__name__
        logger.error(
            f"Failed to generate completion: {str(e)}",
            exc_info=True,
            extra={
                "provider": request.provider,
                "model": request.model,
                "error_type": error_type,
            },
        )
        increment_error_count(error_type)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
