import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status
from src.main import app
from src.api.models import ModelInfo


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_list_outlines_models_success(test_client):
    """Test successful listing of Outlines models."""
    # Create a mock logger that won't raise exceptions
    mock_logger = MagicMock()
    mock_logger.info = AsyncMock()
    mock_logger.error = AsyncMock()

    with patch("src.api.routers.outlines_models.get_request_logger", return_value=mock_logger):
        response = test_client.get(
            "/api/v1/outlines-models",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 4  # We expect 4 models in the list

        # Check the first model (GPT-3.5 Turbo)
        gpt35 = next(m for m in data["models"] if m["id"] == "gpt-3.5-turbo")
        assert gpt35["provider"] == "openai"
        assert gpt35["name"] == "GPT-3.5 Turbo"
        assert gpt35["context_window"] == 4096
        assert gpt35["supports_structured_output"] is True
        assert gpt35["max_output_tokens"] == 2048

        # Check the second model (GPT-4)
        gpt4 = next(m for m in data["models"] if m["id"] == "gpt-4")
        assert gpt4["provider"] == "openai"
        assert gpt4["name"] == "GPT-4"
        assert gpt4["context_window"] == 8192
        assert gpt4["supports_structured_output"] is True
        assert gpt4["max_output_tokens"] == 4096

        # Check the third model (Claude 2)
        claude2 = next(m for m in data["models"] if m["id"] == "claude-2")
        assert claude2["provider"] == "anthropic"
        assert claude2["name"] == "Claude 2"
        assert claude2["context_window"] == 100000
        assert claude2["supports_structured_output"] is True
        assert claude2["max_output_tokens"] == 4096

        # Check the fourth model (Claude 3 Opus)
        claude3 = next(m for m in data["models"] if m["id"] == "claude-3-opus")
        assert claude3["provider"] == "anthropic"
        assert claude3["name"] == "Claude 3 Opus"
        assert claude3["context_window"] == 200000
        assert claude3["supports_structured_output"] is True
        assert claude3["max_output_tokens"] == 4096


@pytest.mark.asyncio
async def test_list_outlines_models_error(test_client):
    """Test error handling when listing Outlines models."""
    # Create a mock logger that raises an exception on info
    mock_logger = MagicMock()
    mock_logger.info = AsyncMock(side_effect=Exception("Test error"))
    mock_logger.error = AsyncMock()

    with patch("src.api.routers.outlines_models.get_request_logger", return_value=mock_logger):
        response = test_client.get(
            "/api/v1/outlines-models",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        assert "Test error" in data["detail"]

        # Verify the logger was called
        mock_logger.info.assert_called_once()
        mock_logger.error.assert_called_once() 