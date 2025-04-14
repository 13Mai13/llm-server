from typing import List

from src.api.routers import api_router
from src.api.models import ModelsResponse, ModelInfo
from llm.providers import get_llm_providers


@api_router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List available models",
    description="Get a list of available language models and their capabilities",
)
async def list_models() -> ModelsResponse:
    """
    List available language models across all providers.
    """
    providers = get_llm_providers()  # TODO: Implement this
    models: List[ModelInfo] = []

    for provider in providers.values():
        provider_models = await provider.list_models()
        models.extend(provider_models)

    return ModelsResponse(models=models)
