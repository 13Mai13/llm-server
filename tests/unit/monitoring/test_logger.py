import logging
import json
import pytest
import io
from src.monitoring.logger import (
    ContextLogger,
    get_request_logger,
    log_request,
    setup_logging,
    JsonFormatter,
)
from src.config import settings


@pytest.fixture(autouse=True)
def setup_test_settings():
    """Set up test settings."""
    # Store original values
    original_log_level = settings.LOG_LEVEL
    original_debug = settings.DEBUG

    # Set test values
    settings.LOG_LEVEL = "DEBUG"
    settings.DEBUG = True

    yield

    # Restore original values
    settings.LOG_LEVEL = original_log_level
    settings.DEBUG = original_debug


@pytest.fixture(autouse=True)
def setup_logging_for_tests(caplog):
    """Set up logging for all tests."""
    # Remove all existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add a test handler that ensures logs are captured by caplog
    caplog.set_level(logging.DEBUG)

    # Set up logging with propagation to root
    setup_logging()

    # Ensure the test logger propagates to root
    test_logger = logging.getLogger("test_logger")
    test_logger.propagate = True
    test_logger.setLevel(logging.DEBUG)

    yield

    # Clean up
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)


def get_last_log_message(caplog):
    """Get the last log message as a dictionary."""
    if not caplog.records:
        return {}

    last_record = caplog.records[-1]

    # Extract the message properly from the record
    try:
        # Try to parse JSON if it's a JSON-formatted log
        message = last_record.getMessage()
        if isinstance(message, str) and message.startswith("{"):
            try:
                return json.loads(message)
            except json.JSONDecodeError:
                pass
    except (AttributeError, TypeError):
        # If not JSON or parsing failed, return the record attributes
        result = {
            "msg": last_record.getMessage(),
            "level": last_record.levelname,
            "name": last_record.name,
        }

    # Add all other attributes from the record
    for key, value in last_record.__dict__.items():
        if key not in result and not key.startswith("_") and not callable(value):
            result[key] = value

    return result


class TestContextLogger:
    def test_basic_logging(self):
        """Test basic logging functionality with context."""
        # Create a StringIO to capture the log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(JsonFormatter())  # Use JSON formatter

        # Create and configure the logger
        logger = ContextLogger("test_logger")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False  # Don't propagate to avoid duplicate logs

        # Set context and log a message
        logger.set_context(request_id="123", user_id="456")
        logger.info("Test message")

        # Get the log output
        log_output = log_capture.getvalue()
        log_data = json.loads(log_output)

        # Verify the content
        assert log_data["message"] == "Test message"
        assert log_data["request_id"] == "123"
        assert log_data["user_id"] == "456"

    def test_context_clearing(self):
        """Test clearing context."""
        # Create a StringIO to capture the log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(JsonFormatter())  # Use JSON formatter

        # Create and configure the logger
        logger = ContextLogger("test_logger")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False

        # Set and clear context
        logger.set_context(request_id="123")
        logger.clear_context()
        logger.info("Test message")

        # Get the log output
        log_output = log_capture.getvalue()
        log_data = json.loads(log_output)

        # Verify the content
        assert log_data["message"] == "Test message"
        assert "request_id" not in log_data

    def test_extra_parameters(self):
        """Test logging with extra parameters."""
        # Create a StringIO to capture the log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(JsonFormatter())  # Use JSON formatter

        # Create and configure the logger
        logger = ContextLogger("test_logger")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False

        # Set context and log with extra parameters
        logger.set_context(request_id="123")
        logger.info("Test message", extra={"additional": "info"})

        # Get the log output
        log_output = log_capture.getvalue()
        log_data = json.loads(log_output)

        # Verify the content
        assert log_data["message"] == "Test message"
        assert log_data["request_id"] == "123"
        assert log_data["additional"] == "info"


class TestRequestLogger:
    def test_get_request_logger(self):
        """Test getting a request logger with context."""
        logger = get_request_logger("test-request-id")
        assert isinstance(logger, ContextLogger)
        assert logger.context.get("request_id") == "test-request-id"

    def test_log_request(self):
        """Test logging a request."""
        # Create a StringIO to capture the log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(JsonFormatter())  # Use JSON formatter

        # Create and configure the logger
        logger = get_request_logger("test-request-id")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False

        # Log a request
        log_request(
            method="GET",
            path="/test",
            status_code=200,
            duration=0.123,
            request_id="test-request-id",
        )

        # Get the log output
        log_output = log_capture.getvalue()
        log_data = json.loads(log_output)

        # Verify the content
        assert log_data["message"] == "Request: GET /test - 200 in 0.123s"
        assert log_data["request_id"] == "test-request-id"
        assert log_data["method"] == "GET"
        assert log_data["path"] == "/test"
        assert log_data["status_code"] == 200
        assert log_data["duration"] == 0.123
