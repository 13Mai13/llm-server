import logging
import sys
import json
from typing import Dict, Any, Optional
import time
import os
from logging.handlers import RotatingFileHandler
import uuid

from src.config import settings


class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the log record.
    
    This formatter is designed to be used with the structured logging system.
    It outputs the log record as a JSON object, making it easier to parse and
    analyze logs in tools like Elasticsearch or Splunk.
    """
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        super().__init__(fmt, datefmt)
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            str: The formatted log record as a JSON string
        """
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith("_") and not callable(value):
                log_data[key] = value
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class ContextLogger(logging.Logger):
    """
    Logger that maintains context information.
    
    This logger allows attaching context information (e.g., request ID,
    user ID) to log records. The context is preserved across log calls.
    """
    
    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs: Any) -> None:
        """
        Set context values.
        
        Args:
            **kwargs: Context values to set
        """
        self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context values."""
        self.context.clear()
    
    def _log(
        self,
        level: int,
        msg: str,
        args: Any,
        exc_info: Any = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Override _log to add context to the log record.
        
        This method adds the context information to the log record
        before passing it to the parent class.
        """
        if extra is None:
            extra = {}
        
        for key, value in self.context.items():
            if key not in extra:
                extra[key] = value
        
        for key, value in kwargs.items():
            if key not in extra:
                extra[key] = value
        
        super()._log(level, msg, args, exc_info, extra, stack_info)


logging.setLoggerClass(ContextLogger)


def setup_logging() -> None:
    """
    Set up the logging system.
    
    This function configures the logging system with appropriate handlers
    and formatters based on the environment.
    """
    root_logger = logging.getLogger()
    
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    json_formatter = JsonFormatter()
    text_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if settings.ENV == "development":
        console_handler.setFormatter(text_formatter)
    else:
        console_handler.setFormatter(json_formatter)
    
    root_logger.addHandler(console_handler)
    
    os.makedirs("logs", exist_ok=True)
    
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(json_formatter)
    
    root_logger.addHandler(file_handler)
    
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialized with level {settings.LOG_LEVEL} in {settings.ENV} environment"
    )


def get_request_logger(request_id: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with request context.
    
    Args:
        request_id: The request ID (optional, will be generated if not provided)
        
    Returns:
        logging.Logger: The logger with request context
    """
    logger = logging.getLogger("request")
    
    context_logger = logger
    if isinstance(logger, ContextLogger):
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        context_logger.set_context(request_id=request_id, timestamp=time.time())
    
    return logger


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration: float,
    request_id: Optional[str] = None,
) -> None:
    """
    Log a request.
    
    Args:
        method: The HTTP method
        path: The request path
        status_code: The response status code
        duration: The request duration in seconds
        request_id: The request ID (optional)
    """
    logger = get_request_logger(request_id)
    logger.info(
        f"Request: {method} {path} - {status_code} in {duration:.3f}s",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration": duration,
        },
    )