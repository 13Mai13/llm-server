import asyncio
from unittest.mock import AsyncMock, patch
import httpx
import pytest_asyncio
import pytest

from src.llm.providers import GroqAPIProvider
from src.config import settings
from src.api.models import ModelInfo, UsageInfo


@pytest.fixture
def mock_groq_settings():
    """Create a mock Groq API key for testing."""
    original_key = settings.GROQ_API_KEY
    settings.GROQ_API_KEY = "test-api-key"
    yield
    settings.GROQ_API_KEY = original_key


@pytest_asyncio.fixture
async def groq_provider(mock_groq_settings):
    """Create a GroqAPIProvider instance for testing."""
    provider = GroqAPIProvider()
    await provider.initialize()
    return provider


@pytest.mark.asyncio
async def test_groq_provider_initialization(groq_provider):
    """Test provider initialization."""
    assert groq_provider.client is not None
    assert groq_provider.name == "openai"
    assert groq_provider.base_url == "https://api.groq.com/openai/v1/"


@pytest.mark.asyncio
async def test_list_models(groq_provider):
    """Test listing available models."""
    models = await groq_provider.list_models()
    
    # Verify models are correctly created
    assert len(models) > 0
    
    # Check a few specific models
    model_ids = [model.id for model in models]
    expected_models = [
        "llama3-8b-8192", 
        "mixtral-8x7b-32768", 
        "gemma2-9b-it", 
        "deepseek-r1-distill-llama-70b"
    ]
    
    for model in expected_models:
        assert model in model_ids
    
    # Verify model info
    for model in models:
        assert isinstance(model, ModelInfo)
        assert model.provider == "openai"
        assert model.context_window > 0
        assert model.max_output_tokens > 0


@pytest.mark.asyncio
async def test_generate_method(groq_provider):
    """Test the generate method with mocked API response."""
    # Prepare mock response
    mock_response = {
        "id": "chatcmpl-123",
        "choices": [{
            "message": {
                "content": "This is a test response from the Groq API."
            }
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }
    
    # Create a mock response object
    mock_response_obj = AsyncMock()
    mock_response_obj.json.return_value = mock_response
    mock_response_obj.raise_for_status.return_value = None
    
    # Patch the client's post method
    with patch.object(groq_provider.client, 'post', return_value=mock_response_obj) as mock_post:
        # Call generate method
        response = await groq_provider.generate(
            model="llama3-8b-8192", 
            prompt="Tell me a short story."
        )
        
        # Verify method calls
        mock_post.assert_called_once_with("/chat/completions", json={
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": "Tell me a short story."}],
            "temperature": 0.7,
            "top_p": 1.0
        })
        
        # Verify the response
        assert response.id == "chatcmpl-123"
        assert response.text == "This is a test response from the Groq API."
        assert response.model == "llama3-8b-8192"
        assert response.provider == "openai"
        
        # Verify usage info
        assert isinstance(response.usage, UsageInfo)
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30



@pytest.mark.asyncio
async def test_generate_unsupported_model(groq_provider):
    """Test generating with an unsupported model raises an error."""
    with pytest.raises(ValueError, match="Model 'unsupported-model' not supported by Groq provider"):
        await groq_provider.generate(
            model="unsupported-model", 
            prompt="This should fail."
        )


@pytest.mark.asyncio
async def test_generate_api_error():
    """Test handling of API errors during generation."""
    # Create provider and initialize
    provider = GroqAPIProvider()
    await provider.initialize()
    
    # Patch the client to raise an HTTP error
    with patch.object(provider.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPStatusError(
            "Error", 
            request=AsyncMock(), 
            response=AsyncMock(status_code=400, text="Bad Request")
        )
        
        # Verify that an error is raised
        with pytest.raises(ValueError, match="Groq API error: 400 - Bad Request"):
            await provider.generate(
                model="llama3-8b-8192", 
                prompt="Test error handling"
            )