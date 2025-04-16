import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_metrics_store():
    """Mock the metrics store."""
    metrics_store_mock = MagicMock()
    metrics_store_mock.get_metrics.return_value = {
        "requests": {
            "total": 100,
            "by_path": {"/api/v1/metrics": 10},
            "by_method": {"GET": 80, "POST": 20},
            "by_status": {200: 95, 500: 5},
            "average_duration": 0.05,
        },
        "llm": {
            "providers": {
                "groq": {
                    "requests": 10,
                    "input_tokens": 1000,
                    "output_tokens": 800,
                    "cost": 0.0025,
                }
            },
            "models": {
                "groq:llama3-8b-8192": {
                    "requests": 8,
                    "input_tokens": 800,
                    "output_tokens": 700,
                    "cost": 0.0020,
                    "timing": {
                        "total": {
                            "average": 1.2,
                            "percentiles": {"p50": 1.0, "p90": 1.5},
                        },
                        "time_to_first_token": {
                            "average": 0.8,
                            "percentiles": {"p50": 0.7, "p90": 1.0},
                        },
                        "time_per_token": {
                            "average": 0.05,
                            "percentiles": {"p50": 0.04, "p90": 0.06},
                        },
                    },
                    "structured_success": 5,
                    "structured_failures": 1,
                    "errors": {"RateLimitError": 2},
                    "rate_limits": 2,
                }
            },
        },
        "batch_processing": {
            "average_batch_size": 5,
            "average_duration": 2.5,
            "success_rate": 0.95,
        },
    }

    with patch(
        "src.api.routers.metrics.get_metrics_store", return_value=metrics_store_mock
    ):
        yield metrics_store_mock


@pytest.fixture
def mock_request_metrics():
    """Mock the request metrics functions."""
    with (
        patch("src.api.routers.metrics.increment_request_count") as mock_inc_req,
        patch("src.api.routers.metrics.increment_error_count") as mock_inc_err,
    ):
        yield mock_inc_req, mock_inc_err


@pytest.fixture
def mock_logger():
    """Mock the logger."""
    logger = MagicMock()
    with patch("src.api.routers.metrics.get_request_logger", return_value=logger):
        yield logger


def test_get_metrics_success(
    test_client, mock_metrics_store, mock_request_metrics, mock_logger
):
    """Test successful retrieval of metrics."""
    mock_inc_req, _ = mock_request_metrics

    response = test_client.get(
        "/api/v1/metrics",
        headers={"X-API-Key": "test-api-key", "X-Request-ID": "test-request-id"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify metrics structure matches what we expect from the metrics store
    assert "requests" in data
    assert "llm" in data
    assert "batch_processing" in data

    # Verify request metrics
    assert data["requests"]["total"] == 100
    assert data["requests"]["by_path"]["/api/v1/metrics"] == 10

    # Verify LLM metrics
    assert data["llm"]["providers"]["groq"]["requests"] == 10
    assert data["llm"]["models"]["groq:llama3-8b-8192"]["requests"] == 8
    assert (
        data["llm"]["models"]["groq:llama3-8b-8192"]["timing"]["total"]["average"]
        == 1.2
    )

    # Verify batch processing metrics
    assert data["batch_processing"]["success_rate"] == 0.95

    # Verify logging and metrics
    mock_logger.info.assert_called_once()
    mock_inc_req.assert_called_once_with(method="GET", path="/metrics", status_code=200)


def test_get_metrics_unauthorized(test_client, mock_request_metrics, mock_logger):
    """Test metrics endpoint without API key."""
    mock_inc_req, _ = mock_request_metrics

    # Make a request without a valid API key
    response = test_client.get(
        "/api/v1/metrics",
        headers={"X-Request-ID": "test-request-id"},
        # No X-API-Key header
    )

    assert response.status_code == 401
    assert "detail" in response.json()

    # Verify logging and metrics
    mock_logger.info.assert_not_called()
    mock_inc_req.assert_not_called()


def test_get_metrics_error(
    test_client, mock_metrics_store, mock_request_metrics, mock_logger
):
    """Test metrics endpoint when metrics retrieval fails."""
    mock_inc_req, mock_inc_err = mock_request_metrics

    # Force an error in metrics retrieval
    mock_metrics_store.get_metrics.side_effect = Exception("Failed to get metrics")

    response = test_client.get(
        "/api/v1/metrics",
        headers={"X-API-Key": "test-api-key", "X-Request-ID": "test-request-id"},
    )

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Failed" in data["detail"]

    # Verify logging and metrics
    mock_logger.error.assert_called_once()
    mock_inc_err.assert_called_once()
    mock_inc_req.assert_called_once_with(method="GET", path="/metrics", status_code=500)
