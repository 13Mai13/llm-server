from fastapi import Depends, HTTPException, status
from typing import List

from src.api.auth import authenticate_request
from src.validation.schema_registry import get_schema_registry
from src.api.models import SchemaDefinition
from src.api.routers import api_router


@api_router.post(
    "/schemas",
    response_model=SchemaDefinition,
    summary="Register a new schema",
    description="Register a new schema for structured output validation",
)
async def register_schema(schema: SchemaDefinition) -> SchemaDefinition:
    """
    Register a new schema for structured output validation.
    """
    schema_registry = get_schema_registry()
    
    try:
        schema_id = await schema_registry.register_schema(
            schema_id=schema.id if schema.id else None,
            name=schema.name,
            description=schema.description,
            schema=schema.schema,
        )
        
        return await schema_registry.get_schema_definition(schema_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@api_router.get(
    "/schemas",
    response_model=List[SchemaDefinition],
    summary="List schemas",
    description="List registered schemas for structured output validation",
    dependencies=[Depends(authenticate_request)],
)
async def list_schemas() -> List[SchemaDefinition]:
    """
    List registered schemas for structured output validation.
    """
    schema_registry = get_schema_registry()
    return await schema_registry.list_schemas()


@api_router.get(
    "/schemas/{schema_id}",
    response_model=SchemaDefinition,
    summary="Get schema by ID",
    description="Get a schema by its ID",
    dependencies=[Depends(authenticate_request)],
)
async def get_schema(schema_id: str) -> SchemaDefinition:
    """
    Get a schema by its ID.
    """
    schema_registry = get_schema_registry()
    schema = await schema_registry.get_schema_definition(schema_id)
    
    if not schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema with ID '{schema_id}' not found",
        )
    
    return schema