import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import httpx
import inspect

from src.config import settings
from src.api.models import ModelInfo, UsageInfo


logger = logging.getLogger(__name__)  # TODO: Check logger


class LLMResponse:
    """Response from an LLM provider."""

    def __init__(
        self,
        id: str,
        text: str,
        usage: UsageInfo,
        model: str,
        provider: str,
    ):
        self.id = id
        self.text = text
        self.usage = usage
        self.model = model
        self.provider = provider


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, name: str):
        self.name = name
        self.client = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider client."""
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """List available models for this provider."""
        pass

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        """Generate text from the model."""
        pass


class GroqAPIProvider(LLMProvider):
    """Provider for Groq API."""

    def __init__(self):
        super().__init__("groq")
        self.api_key = settings.GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1/"
        self.client = None

        # Model capabilities (simplified)
        self.model_info = {
            "llama3-8b-8192": {
                "context_window": 8192,
                "supports_structured_output": True,
                "max_output_tokens": 8192,
            },
            "mixtral-8x7b-32768": {
                "context_window": 32768,
                "supports_structured_output": True,
                "max_output_tokens": 32768,
            },
            "gemma2-9b-it": {
                "context_window": 8192,
                "supports_structured_output": True,
                "max_output_tokens": 8192,
            },
            "deepseek-r1-distill-llama-70b": {
                "context_window": 131072,
                "supports_structured_output": True,
                "max_output_tokens": 131072,
            },
        }

    async def initialize(self) -> None:
        """Initialize the Groq client."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=httpx.Timeout(60.0),
        )
        logger.info("Groq provider initialized")

    async def list_models(self) -> List[ModelInfo]:
        """List available Groq models."""
        models = []

        for model_id, info in self.model_info.items():
            models.append(
                ModelInfo(
                    id=model_id,
                    provider=self.name,
                    name=model_id,  # Using ID as name for simplicity
                    context_window=info["context_window"],
                    supports_structured_output=info["supports_structured_output"],
                    max_output_tokens=info["max_output_tokens"],
                )
            )

        return models

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = 0.7,
        top_p: Optional[float] = 1.0,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        """Generate text from Groq model."""
        if not self.client:
            await self.initialize()

        if model not in self.model_info:
            raise ValueError(f"Model '{model}' not supported by Groq provider")

        # Prepare request payload
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "top_p": top_p,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if stop:
            payload["stop"] = stop

        try:
            response = await self.client.post("/chat/completions", json=payload)
            
            # Check if raise_for_status is a coroutine function (in AsyncMock)
            if inspect.iscoroutinefunction(response.raise_for_status):
                await response.raise_for_status()
            else:
                response.raise_for_status()
            
            # Check if json is a coroutine function (in AsyncMock)
            if inspect.iscoroutinefunction(response.json):
                data = await response.json()
            else:
                data = response.json()

            if not isinstance(data, dict):
                raise ValueError(f"Unexpected response format: {type(data)}")

            text = data["choices"][0]["message"]["content"]

            usage = UsageInfo(
                prompt_tokens=data["usage"]["prompt_tokens"],
                completion_tokens=data["usage"]["completion_tokens"],
                total_tokens=data["usage"]["total_tokens"],
            )

            return LLMResponse(
                id=data["id"],
                text=text,
                usage=usage,
                model=model,
                provider=self.name,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Groq API HTTP error: {e.response.text}")
            raise ValueError(
                f"Groq API error: {e.response.status_code} - {e.response.text}"
            )

        except Exception as e:
            logger.error(f"Unexpected error generating from Groq: {str(e)}")
            raise ValueError(f"Error generating from Groq: {str(e)}")


# Provider registry
_providers: Dict[str, LLMProvider] = {}


def register_provider(provider: LLMProvider) -> None:
    """
    Register an LLM provider.

    Args:
        provider: The provider to register
    """
    _providers[provider.name] = provider
    logger.info(f"Registered provider: {provider.name}")


def get_llm_providers() -> Dict[str, LLMProvider]:
    """
    Get all registered LLM providers.

    Returns:
        Dict[str, LLMProvider]: Dictionary of provider name to provider instance
    """
    return _providers


async def initialize_providers() -> None:
    """Initialize all registered providers."""
    for provider in _providers.values():
        await provider.initialize()


if settings.GROQ_API_KEY:
    register_provider(GroqAPIProvider())
