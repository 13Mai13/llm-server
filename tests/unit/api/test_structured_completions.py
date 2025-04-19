import pytest
from fastapi import status
from unittest.mock import MagicMock, AsyncMock
from src.api.models import UsageInfo
from src.llm.providers import register_provider, get_llm_providers


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.name = "test_provider"
    provider.initialize = AsyncMock()
    provider.generate = AsyncMock()
    provider.generate.return_value = MagicMock(
        text='{"name": "John", "age": 30}',
        id="test-id",
        usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )
    return provider


@pytest.fixture(autouse=True)
def setup_providers(mock_provider):
    """Setup mock providers before each test."""
    # Clear existing providers
    get_llm_providers().clear()
    # Register mock provider
    register_provider(mock_provider)
    yield
    # Cleanup after test
    get_llm_providers().clear()


@pytest.mark.asyncio
async def test_structured_completion_with_schema_id(test_client, mock_provider):
    """Test structured completion with a schema ID."""
    # First register a schema
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    schema_response = test_client.post(
        "/api/v1/schemas",
        headers={"X-API-Key": "test-api-key"},
        json={
            "name": "test_schema",
            "description": "Test schema",
            "json_schema": schema,
        },
    )
    schema_id = schema_response.json()["id"]

    response = test_client.post(
        "/api/v1/structured-completions",
        headers={"X-API-Key": "test-api-key"},
        json={
            "provider": "test_provider",
            "model": "test-model",
            "prompt": "Generate a person's information",
            "schema_id": schema_id,
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 1.0,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == "test-id"
    assert data["provider"] == "test_provider"
    assert data["model"] == "test-model"
    assert data["raw_text"] == '{"name": "John", "age": 30}'
    assert data["structured_output"] == {"name": "John", "age": 30}
    assert data["usage"]["prompt_tokens"] == 10
    assert data["usage"]["completion_tokens"] == 5
    assert data["usage"]["total_tokens"] == 15


@pytest.mark.asyncio
async def test_structured_completion_with_inline_schema(test_client, mock_provider):
    """Test structured completion with an inline schema."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    response = test_client.post(
        "/api/v1/structured-completions",
        headers={"X-API-Key": "test-api-key"},
        json={
            "provider": "test_provider",
            "model": "test-model",
            "prompt": "Generate a person's information",
            "validation_schema": schema,
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 1.0,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == "test-id"
    assert data["provider"] == "test_provider"
    assert data["model"] == "test-model"
    assert data["raw_text"] == '{"name": "John", "age": 30}'
    assert data["structured_output"] == {"name": "John", "age": 30}
    assert data["usage"]["prompt_tokens"] == 10
    assert data["usage"]["completion_tokens"] == 5
    assert data["usage"]["total_tokens"] == 15


@pytest.mark.asyncio
async def test_structured_completion_with_transformers(test_client, mock_provider):
    """Test structured completion with transformers."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    transformers = [{"name": "lowercase_strings", "config": {}}]

    response = test_client.post(
        "/api/v1/structured-completions",
        headers={"X-API-Key": "test-api-key"},
        json={
            "provider": "test_provider",
            "model": "test-model",
            "prompt": "Generate a person's information",
            "validation_schema": schema,
            "transformers": transformers,
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 1.0,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == "test-id"
    assert data["provider"] == "test_provider"
    assert data["model"] == "test-model"
    assert data["raw_text"] == '{"name": "John", "age": 30}'
    assert data["structured_output"] == {"name": "john", "age": 30}
    assert data["usage"]["prompt_tokens"] == 10
    assert data["usage"]["completion_tokens"] == 5
    assert data["usage"]["total_tokens"] == 15


@pytest.mark.asyncio
async def test_structured_completion_invalid_provider(test_client):
    """Test structured completion with an invalid provider."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    response = test_client.post(
        "/api/v1/structured-completions",
        headers={"X-API-Key": "test-api-key"},
        json={
            "provider": "invalid_provider",
            "model": "test-model",
            "prompt": "Generate a person's information",
            "validation_schema": schema,
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 1.0,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_structured_completion_missing_schema(test_client):
    """Test structured completion without a schema."""
    response = test_client.post(
        "/api/v1/structured-completions",
        headers={"X-API-Key": "test-api-key"},
        json={
            "provider": "test_provider",
            "model": "test-model",
            "prompt": "Generate a person's information",
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 1.0,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
