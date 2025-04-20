import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from fastapi.testclient import TestClient
from fastapi import status
from src.llm.providers import LLMProvider
from src.main import app
from src.validation.transformers import TransformerDefinition


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider for testing."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "test_provider"
    provider.generate = AsyncMock()
    type(provider).supports_structured_output = PropertyMock(return_value=True)
    return provider


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
    print(f"Registered schema with ID: {schema_id}")

    # Create a mock for the Outlines model
    mock_outlines_model = MagicMock()
    mock_outlines_model.return_value = {"name": "John", "age": 30}

    # Mock the schema registry
    mock_schema = MagicMock()
    mock_schema.get_schema.return_value = schema
    mock_registry = MagicMock(return_value=mock_schema)

    with (
        patch(
            "src.api.routers.structured_completions.get_llm_providers",
            return_value={"openai": mock_provider},
        ) as mock_get_providers,
        patch(
            "outlines.models.openai", return_value=mock_outlines_model
        ) as mock_openai,
        patch("outlines.generate.json", return_value=mock_outlines_model) as mock_json,
        patch("src.validation.schema_registry.get_schema_registry", mock_registry),
    ):
        # Debug: Print the mocked providers
        providers = mock_get_providers.return_value
        print(f"Mocked providers: {providers.keys()}")

        # Debug: Print the request we're about to send
        request_data = {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "prompt": "Generate a person's information",
            "schema_id": schema_id,
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 1.0,
        }
        print(f"Sending request with data: {request_data}")

        response = test_client.post(
            "/api/v1/structured-completions",
            headers={"X-API-Key": "test-api-key"},
            json=request_data,
        )

        # Debug logging
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        print("Mock calls:")
        print(f"get_llm_providers called: {mock_get_providers.called}")
        print(f"openai called: {mock_openai.called}")
        print(f"json called: {mock_json.called}")
        print(f"get_schema_registry called: {mock_registry.called}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] is not None
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-3.5-turbo"
        assert data["raw_text"] == '{"name": "John", "age": 30}'
        assert data["structured_output"] == {"name": "John", "age": 30}
        assert data["usage"] == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        # Verify the mocks were called correctly
        mock_openai.assert_called_once_with("gpt-3.5-turbo")
        mock_json.assert_called_once_with(
            mock_outlines_model, schema, whitespace_pattern=r"[\n\t ]*", max_tokens=100
        )


@pytest.mark.asyncio
async def test_structured_completion_with_inline_schema(test_client, mock_provider):
    """Test structured completion with an inline schema."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    with (
        patch(
            "src.api.routers.structured_completions.get_llm_providers",
            return_value={"openai": mock_provider},
        ),
        patch("outlines.models.openai") as mock_openai,
        patch("outlines.generate.json") as mock_json,
    ):
        # Mock the OpenAI model
        mock_openai_model = MagicMock()
        mock_openai.return_value = mock_openai_model

        # Mock the generator to return our test output
        mock_generator = MagicMock()
        mock_generator.return_value = {"name": "John", "age": 30}
        mock_json.return_value = mock_generator

        response = test_client.post(
            "/api/v1/structured-completions",
            headers={"X-API-Key": "test-api-key"},
            json={
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "prompt": "Generate a person's information",
                "validation_schema": schema,
                "max_tokens": 100,
                "temperature": 0.7,
                "top_p": 1.0,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] is not None
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-3.5-turbo"
        assert data["raw_text"] == '{"name": "John", "age": 30}'
        assert data["structured_output"] == {"name": "John", "age": 30}
        assert data["usage"] == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        # Verify the mocks were called correctly
        mock_openai.assert_called_once_with("gpt-3.5-turbo")
        mock_json.assert_called_once_with(
            mock_openai_model, schema, whitespace_pattern=r"[\n\t ]*", max_tokens=100
        )
        mock_generator.assert_called_once_with("Generate a person's information")


@pytest.mark.asyncio
async def test_structured_completion_with_transformers(test_client, mock_provider):
    """Test structured completion with transformers."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    transformers = [TransformerDefinition(name="lowercase_strings", config={})]

    with (
        patch(
            "src.api.routers.structured_completions.get_llm_providers",
            return_value={"openai": mock_provider},
        ),
        patch("outlines.models.openai") as mock_openai,
        patch("outlines.generate.json") as mock_json,
        patch(
            "src.api.routers.structured_completions.apply_transformers"
        ) as mock_transform,
    ):
        # Mock the OpenAI model
        mock_openai_model = MagicMock()
        mock_openai.return_value = mock_openai_model

        # Mock the generator to return our test output
        mock_generator = MagicMock()
        mock_generator.return_value = {"name": "John", "age": 30}
        mock_json.return_value = mock_generator

        # Mock the transformer to return lowercase output
        mock_transform.return_value = {"name": "john", "age": 30}

        response = test_client.post(
            "/api/v1/structured-completions",
            headers={"X-API-Key": "test-api-key"},
            json={
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "prompt": "Generate a person's information",
                "validation_schema": schema,
                "transformers": [{"name": "lowercase_strings", "config": {}}],
                "max_tokens": 100,
                "temperature": 0.7,
                "top_p": 1.0,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] is not None
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-3.5-turbo"
        assert data["raw_text"] == '{"name": "john", "age": 30}'
        assert data["structured_output"] == {"name": "john", "age": 30}
        assert data["usage"] == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        # Verify the mocks were called correctly
        mock_openai.assert_called_once_with("gpt-3.5-turbo")
        mock_json.assert_called_once_with(
            mock_openai_model, schema, whitespace_pattern=r"[\n\t ]*", max_tokens=100
        )
        mock_generator.assert_called_once_with("Generate a person's information")
        mock_transform.assert_called_once_with(
            {"name": "John", "age": 30}, transformers
        )


@pytest.mark.asyncio
async def test_structured_completion_invalid_provider(test_client):
    """Test structured completion with an invalid provider."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    with patch(
        "src.api.routers.structured_completions.get_llm_providers", return_value={}
    ):
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
    with patch(
        "src.api.routers.structured_completions.get_llm_providers",
        return_value={"openai": mock_provider},
    ):
        response = test_client.post(
            "/api/v1/structured-completions",
            headers={"X-API-Key": "test-api-key"},
            json={
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "prompt": "Generate a person's information",
                "max_tokens": 100,
                "temperature": 0.7,
                "top_p": 1.0,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
