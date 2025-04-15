import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status

from src.api.models import UsageInfo
from src.llm.providers import LLMProvider, LLMResponse
from src.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_providers():
    """Create mock LLM providers for testing."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "test_provider"
    provider.generate = AsyncMock()

    mock_response = LLMResponse(
        id="resp-123",
        text="This is a test response",
        usage=UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        model="test_model",
        provider="test_provider",
    )
    provider.generate.return_value = mock_response

    return {"test_provider": provider}


@pytest.fixture
def mock_metrics():
    """Create a mock for the metrics recorder context manager."""
    with patch("src.api.routers.completions.record_request_metrics") as mock:
        mock.return_value.__enter__ = MagicMock(return_value=None)
        mock.return_value.__exit__ = MagicMock(return_value=None)
        yield mock


@pytest.mark.asyncio
async def test_create_completion_success(client, mock_providers, mock_metrics):
    """Test successful text completion generation."""
    with patch(
        "src.api.routers.completions.get_llm_providers", return_value=mock_providers
    ):
        # Make the request
        response = client.post(
            "/api/v1/completions",
            json={
                "provider": "test_provider",
                "model": "test_model",
                "prompt": "Hello, world!",
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 100,
                "stop": ["END"],
            },
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["id"] == "resp-123"
        assert data["provider"] == "test_provider"
        assert data["model"] == "test_model"
        assert data["text"] == "This is a test response"
        assert data["usage"]["prompt_tokens"] == 10
        assert data["usage"]["completion_tokens"] == 20
        assert data["usage"]["total_tokens"] == 30

        mock_providers["test_provider"].generate.assert_called_once_with(
            model="test_model",
            prompt="Hello, world!",
            temperature=0.7,
            top_p=0.9,
            max_tokens=100,
            stop=["END"],
        )

        mock_metrics.assert_called_once_with("test_provider", "test_model")


@pytest.mark.asyncio
async def test_create_completion_unsupported_provider(client):
    """Test error handling for an unsupported provider."""
    with patch("src.api.routers.completions.get_llm_providers", return_value={}):
        response = client.post(
            "/api/v1/completions",
            json={
                "provider": "nonexistent_provider",
                "model": "test_model",
                "prompt": "Hello, world!",
            },
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        data = response.json()
        assert "detail" in data
        assert "not supported" in data["detail"]
        assert "nonexistent_provider" in data["detail"]


@pytest.mark.asyncio
async def test_create_completion_provider_error(client, mock_providers, mock_metrics):
    """Test error handling when the provider raises an exception."""
    mock_providers["test_provider"].generate.side_effect = ValueError("Model error")

    with patch(
        "src.api.routers.completions.get_llm_providers", return_value=mock_providers
    ):
        response = client.post(
            "/api/v1/completions",
            json={
                "provider": "test_provider",
                "model": "test_model",
                "prompt": "Hello, world!",
            },
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        data = response.json()
        assert "detail" in data
        assert "Model error" in data["detail"]

        mock_providers["test_provider"].generate.assert_called_once()

        mock_metrics.assert_called_once()


@pytest.mark.asyncio
async def test_create_completion_missing_required_fields(client):
    """Test validation for missing required fields."""
    response = client.post(
        "/api/v1/completions",
        json={
            "provider": "test_provider"
            # Missing model and prompt
        },
        headers={"X-API-Key": "test-api-key"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    data = response.json()
    assert "detail" in data
    errors = {error["loc"][-1]: error["msg"] for error in data["detail"]}
    assert "model" in errors
    assert "prompt" in errors


@pytest.mark.asyncio
async def test_create_completion_invalid_parameters(client, mock_providers):
    """Test validation for invalid parameter values."""
    with patch(
        "src.api.routers.completions.get_llm_providers", return_value=mock_providers
    ):
        response = client.post(
            "/api/v1/completions",
            json={
                "provider": "test_provider",
                "model": "test_model",
                "prompt": "Hello, world!",
                "temperature": 2.0,  # Invalid: should be between 0 and 1
                "top_p": -0.5,  # Invalid: should be between 0 and 1
            },
            headers={"X-API-Key": "test-api-key"},
        )

        data = response.json()
        assert "detail" in data
        errors = {error["loc"][-1]: error["msg"] for error in data["detail"]}
        assert "temperature" in errors or "top_p" in errors


@pytest.mark.asyncio
async def test_create_completion_unauthorized(client):
    """Test authorization check."""
    response = client.post(
        "/api/v1/completions",
        json={
            "provider": "test_provider",
            "model": "test_model",
            "prompt": "Hello, world!",
        },
        # No API key header
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
