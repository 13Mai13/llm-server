"""
Pydantic base class with the settings
"""

from typing import Optional, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # API settings
    API_KEY: Optional[str] = None
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # LLM Provider settings
    GROQ_API_KEY: Optional[str] = None

    # Connection pool settings
    CONNECTION_TIMEOUT: float = 10.0
    KEEPALIVE_TIMEOUT: float = 60.0
    MAX_CONNECTIONS: int = 10

    # Timeouts and retry settings
    REQUEST_TIMEOUT: float = 30.0
    CONNECT_TIMEOUT: float = 5.0
    READ_TIMEOUT: float = 30.0

    # Rate limiting and retry mechanism
    MAX_REQUESTS_PER_MINUTE: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0  # seconds
    RETRY_BACKOFF_FACTOR: float = 1.5  # Exponential backoff

    # Logging and monitoring
    ERROR_TRACKING_ENABLED: bool = False
    PERFORMANCE_LOGGING: bool = False

    # Provider settings
    DEFAULT_PROVIDER: str = "groq"
    DEFAULT_MODEL: Dict[str, str] = {
        "groq": "llama3-8b-8192",
    }

    # Optional advanced settings
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIME: float = 30.0  # seconds

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    def get_model_for_provider(self, provider: Optional[str] = None) -> str:
        """Get the default model for a provider."""
        provider = provider or self.DEFAULT_PROVIDER
        return self.DEFAULT_MODEL.get(provider, "")

    def get_api_key_for_provider(self, provider: Optional[str] = None) -> Optional[str]:
        """Get the API key for a provider."""
        provider = provider or self.DEFAULT_PROVIDER

        provider_api_keys = {
            "groq": self.GROQ_API_KEY,
            # Add other providers here as needed
        }
        return provider_api_keys.get(provider)


# Create a global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get application settings.

    Returns:
        Settings: Application settings
    """
    return settings
