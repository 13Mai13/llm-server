import logging
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from src.config import get_settings, Settings

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def authenticate_request(
    request: Request,
    api_key: str = Depends(API_KEY_HEADER),
    settings: Settings = Depends(get_settings)
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
    
    if not api_key:
        api_key = request.query_params.get("api_key")
    
    if not api_key:
        api_key = request.cookies.get("api_key")

    
    
    if not api_key or api_key != settings.API_KEY:
        logger.warning(
            f"Authentication failed for request from {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return True