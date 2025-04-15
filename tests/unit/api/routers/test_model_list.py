import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.api.models import ModelInfo
from src.llm.providers import LLMProvider
from src.main import app  # Assuming your FastAPI app is defined here


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_providers():
    """Create mock LLM providers for testing."""
    # Create mock provider 1
    provider1 = MagicMock(spec=LLMProvider)
    provider1.name = "provider1"
    provider1.list_models = AsyncMock(
        return_value=[
            ModelInfo(
                id="model1",
                provider="provider1",
                name="Model 1",
                context_window=4096,
                supports_structured_output=True,
                max_output_tokens=2048,
            ),
            ModelInfo(
                id="model2",
                provider="provider1",
                name="Model 2",
                context_window=8192,
                supports_structured_output=False,
                max_output_tokens=4096,
            ),
        ]
    )

    # Create mock provider 2
    provider2 = MagicMock(spec=LLMProvider)
    provider2.name = "provider2"
    provider2.list_models = AsyncMock(
        return_value=[
            ModelInfo(
                id="model3",
                provider="provider2",
                name="Model 3",
                context_window=16384,
                supports_structured_output=True,
                max_output_tokens=8192,
            )
        ]
    )

    return {"provider1": provider1, "provider2": provider2}


@pytest.mark.asyncio
async def test_list_models(client, mock_providers):
    """Test that the /models endpoint correctly lists all models from all providers."""

    with patch(
        "src.api.routers.model_list.get_llm_providers", return_value=mock_providers
    ):
        response = client.get("/api/v1/models", headers={"X-API-Key": "test-api-key"})

        assert response.status_code == 200

        data = response.json()

        assert "models" in data
        models = data["models"]

        assert len(models) == 3

        model_ids = [model["id"] for model in models]
        assert "model1" in model_ids
        assert "model2" in model_ids
        assert "model3" in model_ids

        for model in models:
            if model["id"] in ["model1", "model2"]:
                assert model["provider"] == "provider1"
            elif model["id"] == "model3":
                assert model["provider"] == "provider2"

        for provider in mock_providers.values():
            provider.list_models.assert_called_once()


@pytest.mark.asyncio
async def test_list_models_no_providers(client):
    """Test the /models endpoint when no providers are available."""
    with patch("src.api.routers.model_list.get_llm_providers", return_value={}):
        response = client.get("/api/v1/models", headers={"X-API-Key": "test-api-key"})

        assert response.status_code == 200

        data = response.json()

        assert "models" in data
        models = data["models"]

        assert len(models) == 0
