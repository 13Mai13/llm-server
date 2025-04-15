from typing import List
from fastapi import Request
from src.api.routers import api_router
from src.api.models import ModelsResponse, ModelInfo
from src.llm.providers import get_llm_providers
from src.monitoring.metrics import increment_error_count
from src.monitoring.logger import get_request_logger

logger = get_request_logger()


@api_router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List available models",
    description="Get a list of available language models and their capabilities",
)
async def list_models(fastapi_request: Request) -> ModelsResponse:
    """
    List available language models across all providers.
    """
    request_id = fastapi_request.headers.get("X-Request-ID", "unknown")
    logger = get_request_logger(request_id)

    try:
        logger.info("Fetching available models from all providers")

        providers = get_llm_providers()
        models: List[ModelInfo] = []

        for provider_name, provider in providers.items():
            try:
                provider_models = await provider.list_models()
                models.extend(provider_models)
                logger.info(
                    f"Retrieved {len(provider_models)} models from provider {provider_name}",
                    extra={
                        "provider": provider_name,
                        "model_count": len(provider_models),
                    },
                )
            except Exception as e:
                error_type = type(e).__name__
                logger.error(
                    f"Failed to fetch models from provider {provider_name}: {str(e)}",
                    exc_info=True,
                    extra={
                        "provider": provider_name,
                        "error_type": error_type,
                    },
                )
                increment_error_count(f"provider_{error_type}")

        logger.info(
            f"Successfully retrieved {len(models)} models from all providers",
            extra={"total_models": len(models)},
        )

        return ModelsResponse(models=models)
    except Exception as e:
        error_type = type(e).__name__
        logger.error(
            "Failed to list models",
            exc_info=True,
            extra={"error_type": error_type},
        )
        increment_error_count(error_type)
        raise
