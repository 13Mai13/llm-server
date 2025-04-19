import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_register_schema(test_client):
    """Test registering a new schema."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    response = test_client.post(
        "/api/v1/schemas",
        headers={"X-API-Key": "test-api-key"},
        json={
            "name": "test_schema",
            "description": "Test schema",
            "json_schema": schema,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert data["name"] == "test_schema"
    assert data["description"] == "Test schema"
    assert data["json_schema"] == schema


@pytest.mark.asyncio
async def test_register_schema_with_id(test_client):
    """Test registering a schema with a specific ID."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    response = test_client.post(
        "/api/v1/schemas",
        headers={"X-API-Key": "test-api-key"},
        json={
            "id": "test-id",
            "name": "test_schema",
            "description": "Test schema",
            "json_schema": schema,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == "test-id"
    assert data["name"] == "test_schema"
    assert data["description"] == "Test schema"
    assert data["json_schema"] == schema


@pytest.mark.asyncio
async def test_register_schema_invalid(test_client):
    """Test registering an invalid schema."""
    response = test_client.post(
        "/api/v1/schemas",
        headers={"X-API-Key": "test-api-key"},
        json={
            "name": "test_schema",
            "description": "Test schema",
            "json_schema": "invalid schema",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_list_schemas(test_client):
    """Test listing all schemas."""
    # First register a schema
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    test_client.post(
        "/api/v1/schemas",
        headers={"X-API-Key": "test-api-key"},
        json={
            "name": "test_schema",
            "description": "Test schema",
            "json_schema": schema,
        },
    )

    # Then list schemas
    response = test_client.get("/api/v1/schemas", headers={"X-API-Key": "test-api-key"})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(item, dict) for item in data)
    assert any(item["name"] == "test_schema" for item in data)
