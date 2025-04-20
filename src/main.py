import uvicorn
from fastapi import FastAPI
from src.api.routers import (
    health,
    model_list,
    completions,
    metrics,
    schema_registry,
    structured_completions,
    outlines_models,
)
from src.config import get_settings

settings = get_settings()

# TODO: Set configs better


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title="LLM Inference Server",
        description="High-performance LLM inference server with structured and unstructured output validation",
        version="0.1.0",
        # lifespan=lifespan, #TODO: Set lifespan
    )

    app.include_router(health.api_router)
    app.include_router(model_list.api_router)
    app.include_router(completions.api_router)
    app.include_router(metrics.api_router)
    app.include_router(schema_registry.api_router)
    app.include_router(structured_completions.api_router)
    app.include_router(outlines_models.api_router)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
