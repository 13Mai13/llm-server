"""
Pydantic base class with the settings
"""

import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    This class uses Pydantic's BaseSettings which automatically reads
    from environment variables matching the field names.
    """
    # API settings
    API_KEY: Optional[str] = None
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # LLM Provider settings
    GROQ_API_KEY: Optional[str] = None
    
    # Default LLM settings
    DEFAULT_PROVIDER: str = "groq" 
    DEFAULT_MODEL: Dict[str, str] = {
        "groq": "llama3-8b-8192",
        "openai": "gpt-3.5-turbo",
        "anthropic": "claude-instant-1"
    }
    
    # Request settings
    REQUEST_TIMEOUT: float = 30.0
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0  # seconds
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    def get_model_for_provider(self, provider: Optional[str] = None) -> str:
        """Get the default model for a provider."""
        provider = provider or self.DEFAULT_PROVIDER
        return self.DEFAULT_MODEL.get(provider, "")

    def get_api_key_for_provider(self, provider: Optional[str] = None) -> Optional[str]:
        """Get the API key for a provider."""
        provider = provider or self.DEFAULT_PROVIDER
        
        if provider == "groq":
            return self.GROQ_API_KEY
        return None


# Create a global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get application settings.
    
    Returns:
        Settings: Application settings
    """
    return settings