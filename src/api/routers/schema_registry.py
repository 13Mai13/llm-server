from fastapi import HTTPException, status
from typing import List

from src.validation.schema_registry import get_schema_registry
from src.api.models import SchemaDefinition
from src.api.routers import api_router


@api_router.post(
    "/schemas",
    response_model=SchemaDefinition,
    status_code=status.HTTP_201_CREATED,
)
async def register_schema(schema: SchemaDefinition) -> SchemaDefinition:
    """
    Register a new schema.
    """
    schema_registry = get_schema_registry()

    try:
        schema_id = await schema_registry.register_schema(
            schema=schema.json_schema,
            name=schema.name,
            description=schema.description,
            schema_id=schema.id,
        )

        return await schema_registry.get_schema_definition(schema_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@api_router.get("/schemas", response_model=List[SchemaDefinition])
async def list_schemas() -> List[SchemaDefinition]:
    """
    List all registered schemas.
    """
    schema_registry = get_schema_registry()
    return await schema_registry.list_schemas()


@api_router.get("/schemas/{schema_id}", response_model=SchemaDefinition)
async def get_schema(schema_id: str) -> SchemaDefinition:
    """
    Get a schema by ID.
    """
    schema_registry = get_schema_registry()
    schema = await schema_registry.get_schema_definition(schema_id)

    if not schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema with ID '{schema_id}' not found",
        )

    return schema


@api_router.delete("/schemas/{schema_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schema(schema_id: str) -> None:
    """
    Delete a schema.
    """
    schema_registry = get_schema_registry()
    if not await schema_registry.delete_schema(schema_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema with ID '{schema_id}' not found",
        )


@api_router.put("/schemas/{schema_id}", response_model=SchemaDefinition)
async def update_schema(
    schema_id: str,
    schema: SchemaDefinition,
) -> SchemaDefinition:
    """
    Update a schema.
    """
    schema_registry = get_schema_registry()
    updated_schema = await schema_registry.update_schema(
        schema_id=schema_id,
        schema=schema.json_schema,
        name=schema.name,
        description=schema.description,
    )

    if not updated_schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema with ID '{schema_id}' not found",
        )

    return updated_schema
