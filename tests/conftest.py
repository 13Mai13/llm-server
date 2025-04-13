import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app
from src.config import Settings

import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

@pytest.fixture
def test_settings():
    """Return test settings with predefined values."""
    return Settings(
        API_KEY="test-api-key",
        DEBUG=True,
        LOG_LEVEL="INFO",
        HOST="127.0.0.1",
        PORT=8000,
        GROQ_API_KEY="test-groq-key",
    )

@pytest.fixture
def test_client(test_settings):
    """Return a test client with mocked settings."""
    with patch("src.config.get_settings", return_value=test_settings):
        with TestClient(app) as client:
            yield client
