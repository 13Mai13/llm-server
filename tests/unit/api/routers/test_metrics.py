import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_metrics():
    """Mock the metrics store."""
    with patch("src.api.routers.metrics.get_metrics") as mock:
        mock.return_value = {
            "errors": {
                "total": 5,
                "by_type": {
                    "Exception": 3,
                    "HTTPException": 2
                }
            },
            "llm": {
                "requests": {
                    "groq": 10,
                    "groq:llama3-8b-8192": 8
                },
                "tokens": {
                    "groq": 1000,
                    "groq:llama3-8b-8192": 800
                }
            },
        }
        yield mock


@pytest.fixture
def mock_request_metrics():
    """Mock the request metrics functions."""
    with patch("src.api.routers.metrics.increment_request_count") as mock_inc_req, \
         patch("src.api.routers.metrics.increment_error_count") as mock_inc_err:
        yield mock_inc_req, mock_inc_err


@pytest.fixture
def mock_logger():
    """Mock the logger."""
    logger = MagicMock()
    with patch("src.api.routers.metrics.get_request_logger", return_value=logger):
        yield logger


def test_get_metrics_success(test_client, mock_metrics, mock_request_metrics, mock_logger):
    """Test successful retrieval of metrics."""
    mock_inc_req, _ = mock_request_metrics
    
    response = test_client.get(
        "/api/v1/metrics",
        headers={
            "X-API-Key": "test-api-key",
            "X-Request-ID": "test-request-id"
        }
    )

    assert response.status_code == 200
    data = response.json()
    
    # Verify metrics structure
    assert "errors" in data
    assert "llm" in data
    
    # Verify error metrics
    assert data["errors"]["total"] == 5
    assert data["errors"]["by_type"]["Exception"] == 3
    assert data["errors"]["by_type"]["HTTPException"] == 2
    
    # Verify LLM metrics
    assert data["llm"]["requests"]["groq"] == 10
    assert data["llm"]["requests"]["groq:llama3-8b-8192"] == 8
    assert data["llm"]["tokens"]["groq"] == 1000
    assert data["llm"]["tokens"]["groq:llama3-8b-8192"] == 800

    # Verify logging and metrics
    mock_logger.info.assert_called_once()
    mock_inc_req.assert_called_once()


def test_get_metrics_unauthorized(test_client, mock_request_metrics, mock_logger):
    """Test metrics endpoint without API key."""
    mock_inc_req, _ = mock_request_metrics
    
    # Make a request without a valid API key
    response = test_client.get(
        "/api/v1/metrics",
        headers={"X-Request-ID": "test-request-id"}
        # No X-API-Key header
    )
    
    assert response.status_code == 401
    assert "detail" in response.json()
    
    # Verify logging and metrics
    mock_logger.info.assert_not_called()
    mock_inc_req.assert_not_called()


def test_get_metrics_error(test_client, mock_metrics, mock_request_metrics, mock_logger):
    """Test metrics endpoint when metrics retrieval fails."""
    mock_inc_req, mock_inc_err = mock_request_metrics
    
    # Force an error in metrics retrieval
    mock_metrics.side_effect = Exception("Failed to get metrics")
    
    response = test_client.get(
        "/api/v1/metrics",
        headers={
            "X-API-Key": "test-api-key",
            "X-Request-ID": "test-request-id"
        }
    )
    
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Failed" in data["detail"]
    
    # Verify logging and metrics
    mock_logger.error.assert_called_once()
    mock_inc_err.assert_called_once()
    mock_inc_req.assert_called_once()