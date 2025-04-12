import logging
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader
import os

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# TODO: Change how to load the env
from main import load_configs
load_configs()

async def authenticate_request(
    request: Request,
    api_key: str = Depends(API_KEY_HEADER)
) -> bool:
    """
    Authenticate the request using API key.
    
    Args:
        request: The incoming request
        api_key: The API key from the header
        
    Returns:
        bool: True if authentication is successful
        
    Raises:
        HTTPException: If authentication fails
    """
    # Skip authentication for development mode if enabled
    if os.getenv("MODE"):
        return True
    
    if not api_key:
        api_key = request.query_params.get("api_key")
    
    if not api_key:
        api_key = request.cookies.get("api_key")
    
    if not api_key or api_key != os.getenv("API_KEY_FOR_AUTH"):
        logger.warning(
            f"Authentication failed for request from {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return True