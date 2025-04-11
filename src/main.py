import uvicorn
from fastapi import FastAPI


app = FastAPI(
    title="LLM Inference Server",
    description="Simple API for LLM inference",
    version="0.1.0",
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": 200, "version": app.version}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
