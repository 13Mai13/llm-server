import logging
import time
from typing import Dict, Any, Optional, ContextManager
from contextlib import contextmanager
import threading

from src.config import settings


logger = logging.getLogger(__name__)


class MetricsStore:
    """
    Simple in-memory store for metrics.
    
    This class provides methods for tracking various metrics like
    request counts, error counts, and processing times.
    
    In a production environment, this would be replaced with a proper
    metrics system like Prometheus or Datadog.
    """
    
    def __init__(self):
        """Initialize the metrics store."""
        self.request_count = 0
        self.error_count = 0
        self.request_duration_sum = 0.0
        self.request_duration_count = 0
        
        # More detailed metrics
        self.requests_by_path: Dict[str, int] = {}
        self.requests_by_method: Dict[str, int] = {}
        self.requests_by_status: Dict[int, int] = {}
        self.errors_by_type: Dict[str, int] = {}
        
        # LLM provider metrics
        self.llm_requests: Dict[str, int] = {}  # by provider
        self.llm_tokens: Dict[str, int] = {}  # by provider
        
        # Validation metrics
        self.validation_successes = 0
        self.validation_failures = 0
        
        # Thread safety
        self.lock = threading.Lock()
    
    def increment_request_count(
        self,
        method: Optional[str] = None,
        path: Optional[str] = None,
        status_code: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> None:
        """
        Increment the request count and related metrics.
        
        Args:
            method: The HTTP method
            path: The request path
            status_code: The response status code
            duration: The request duration in seconds
        """
        with self.lock:
            self.request_count += 1
            
            if method:
                self.requests_by_method[method] = self.requests_by_method.get(method, 0) + 1
            
            if path:
                self.requests_by_path[path] = self.requests_by_path.get(path, 0) + 1
            
            if status_code:
                self.requests_by_status[status_code] = self.requests_by_status.get(status_code, 0) + 1
            
            if duration:
                self.request_duration_sum += duration
                self.request_duration_count += 1
    
    def increment_error_count(self, error_type: Optional[str] = None) -> None:
        """
        Increment the error count.
        
        Args:
            error_type: The type of error
        """
        with self.lock:
            self.error_count += 1
            
            if error_type:
                self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
    
    def record_llm_request(
        self,
        provider: str,
        model: str,
        tokens: int,
        duration: float,
        structured: bool = False,
    ) -> None:
        """
        Record metrics for an LLM request.
        
        Args:
            provider: The LLM provider name
            model: The model name
            tokens: The number of tokens used
            duration: The request duration in seconds
            structured: Whether the request was for structured output
        """
        with self.lock:
            # Track by provider
            provider_key = provider
            self.llm_requests[provider_key] = self.llm_requests.get(provider_key, 0) + 1
            self.llm_tokens[provider_key] = self.llm_tokens.get(provider_key, 0) + tokens
            
            # Track by model
            model_key = f"{provider}:{model}"
            self.llm_requests[model_key] = self.llm_requests.get(model_key, 0) + 1
            self.llm_tokens[model_key] = self.llm_tokens.get(model_key, 0) + tokens
            
            # Track structured requests
            if structured:
                structured_key = f"{provider}:{model}:structured"
                self.llm_requests[structured_key] = self.llm_requests.get(structured_key, 0) + 1
    
    def record_validation_result(self, success: bool) -> None:
        """
        Record a validation result.
        
        Args:
            success: Whether validation was successful
        """
        with self.lock:
            if success:
                self.validation_successes += 1
            else:
                self.validation_failures += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics.
        
        Returns:
            Dict[str, Any]: The metrics
        """
        with self.lock:
            return {
                "requests": {
                    "total": self.request_count,
                    "by_path": self.requests_by_path,
                    "by_method": self.requests_by_method,
                    "by_status": self.requests_by_status,
                    "average_duration": (
                        self.request_duration_sum / self.request_duration_count
                        if self.request_duration_count > 0
                        else 0
                    ),
                }
            }


# Global metrics store
_metrics_store = MetricsStore()


def get_metrics_store() -> MetricsStore:
    """
    Get the global metrics store.
    
    Returns:
        MetricsStore: The metrics store
    """
    return _metrics_store


def increment_request_count(
    method: Optional[str] = None,
    path: Optional[str] = None,
    status_code: Optional[int] = None,
    duration: Optional[float] = None,
) -> None:
    """
    Increment the request count and related metrics.
    
    Args:
        method: The HTTP method
        path: The request path
        status_code: The response status code
        duration: The request duration in seconds
    """
    _metrics_store.increment_request_count(method, path, status_code, duration)


def increment_error_count(error_type: Optional[str] = None) -> None:
    """
    Increment the error count.
    
    Args:
        error_type: The type of error
    """
    _metrics_store.increment_error_count(error_type)


@contextmanager
def record_request_metrics(
    provider: str,
    model: str,
    structured: bool = False,
) -> ContextManager[None]:
    """
    Context manager for recording LLM request metrics.
    
    This context manager tracks the duration of the request and increments
    the appropriate metrics.
    
    Args:
        provider: The LLM provider name
        model: The model name
        structured: Whether the request was for structured output
        
    Yields:
        None
    """
    start_time = time.time()
    tokens = 0
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        _metrics_store.record_llm_request(provider, model, tokens, duration, structured)


def record_validation_result(success: bool) -> None:
    """
    Record a validation result.
    
    Args:
        success: Whether validation was successful
    """
    _metrics_store.record_validation_result(success)


def get_metrics() -> Dict[str, Any]:
    """
    Get all metrics.
    
    Returns:
        Dict[str, Any]: The metrics
    """
    return {
                "errors": {
                    "total": _metrics_store.error_count,
                    "by_type": _metrics_store.errors_by_type,
                },
                "llm": {
                    "requests": _metrics_store.llm_requests,
                    "tokens": _metrics_store.llm_tokens,
                },
                "validation": {
                    "successes": _metrics_store.validation_successes,
                    "failures": _metrics_store.validation_failures,
                    "success_rate": (
                        _metrics_store.validation_successes
                        / (_metrics_store.validation_successes + _metrics_store.validation_failures)
                        if _metrics_store.validation_successes + _metrics_store.validation_failures > 0
                        else 0
                    ),
                },
            }