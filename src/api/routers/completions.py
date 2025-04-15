from fastapi import HTTPException, status
from src.api.routers import api_router

from src.llm.providers import get_llm_providers
from src.monitoring.metrics import record_request_metrics
from src.api.models import (
    CompletionRequest, 
    CompletionResponse,
    ErrorResponse,
)

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
async def create_completion(request: CompletionRequest) -> CompletionResponse:
    """
    Generate a text completion from a prompt without structured validation.
    """
    providers = get_llm_providers()
    
    if request.provider not in providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{request.provider}' not supported",
        )
    
    provider = providers[request.provider]
    
    try:
        # Record metrics for the request
        with record_request_metrics(request.provider, request.model):
            response = await provider.generate(
                model=request.model,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                stop=request.stop,
            )
        
        return CompletionResponse(
            id=response.id,
            provider=request.provider,
            model=request.model,
            text=response.text,
            usage=response.usage,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )