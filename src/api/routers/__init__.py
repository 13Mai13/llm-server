from fastapi import APIRouter, Depends
from src.api.auth import authenticate_request

api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(authenticate_request)]  # All routers under auth
)