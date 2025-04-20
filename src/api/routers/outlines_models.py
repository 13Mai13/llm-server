from typing import List
from fastapi import Request, HTTPException, status
from src.api.routers import api_router
from src.api.models import ModelsResponse, ModelInfo
from src.monitoring.metrics import increment_error_count
from src.monitoring.logger import get_request_logger


@api_router.get(
    "/outlines-models",
    response_model=ModelsResponse,
    summary="List available Outlines models",
    description="Get a list of available language models that can be used with Outlines for structured output",
)
async def list_outlines_models(fastapi_request: Request) -> ModelsResponse:
    """
    List available language models that can be used with Outlines.
    """
    request_id = fastapi_request.headers.get("X-Request-ID", "unknown")
    logger = get_request_logger(request_id)

    try:
        await logger.info("Fetching available Outlines models")

        # Define a list of known models that work well with Outlines
        outlines_models: List[ModelInfo] = [
            ModelInfo(
                id="gpt-3.5-turbo",
                provider="openai",
                name="GPT-3.5 Turbo",
                context_window=4096,
                supports_structured_output=True,
                max_output_tokens=2048,
            ),
            ModelInfo(
                id="gpt-4",
                provider="openai",
                name="GPT-4",
                context_window=8192,
                supports_structured_output=True,
                max_output_tokens=4096,
            ),
            ModelInfo(
                id="claude-2",
                provider="anthropic",
                name="Claude 2",
                context_window=100000,
                supports_structured_output=True,
                max_output_tokens=4096,
            ),
            ModelInfo(
                id="claude-3-opus",
                provider="anthropic",
                name="Claude 3 Opus",
                context_window=200000,
                supports_structured_output=True,
                max_output_tokens=4096,
            ),
        ]

        await logger.info(
            f"Successfully retrieved {len(outlines_models)} Outlines models",
            extra={"total_models": len(outlines_models)},
        )

        return ModelsResponse(models=outlines_models)
    except Exception as e:
        error_type = type(e).__name__
        await logger.error(
            "Failed to list Outlines models",
            exc_info=True,
            extra={"error_type": error_type},
        )
        increment_error_count(error_type)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
