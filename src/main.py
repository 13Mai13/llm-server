import uvicorn
from fastapi import FastAPI
from src.api.routers import health
from src.config import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title="LLM Inference Server",
        description="High-performance LLM inference server with structured output validation",
        version="0.1.0",
        # lifespan=lifespan, #TODO: Set lifespan
    )

    app.include_router(health.api_router)

    return app


app = create_app()


# @app.post("/completions")
# async def create_completion(prompt: str):
#     """
#     Generate a text completion from a prompt using Groq
#     """
#     if not groq_api_key:
#         raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.post(
#                 "https://api.groq.com/openai/v1/chat/completions",
#                 headers={
#                     "Authorization": f"Bearer {groq_api_key}",
#                     "Content-Type": "application/json"
#                 },
#                 json={
#                     "model": "llama3-8b-8192",
#                     "messages": [{"role": "user", "content": prompt}]
#                 },
#                 timeout=30.0
#             )
#             response.raise_for_status()
#             data = response.json()

#             return data

#         except httpx.HTTPStatusError as e:
#             raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
