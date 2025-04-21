import logging
import time
from typing import Dict, Any, Optional, ContextManager, List
from contextlib import contextmanager
import threading
from dataclasses import dataclass
from datetime import datetime
import statistics


logger = logging.getLogger(__name__)


@dataclass
class LLMRequestMetrics:
    """Detailed metrics for a single LLM request."""

    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    duration: float
    time_to_first_token: float
    time_per_token: float
    cost: float
    structured: bool
    timestamp: datetime
    success: bool
    error_type: Optional[str] = None


class MetricsStore:
    """
    Enhanced metrics store for LLM operations.
    """

    def __init__(self):
        """Initialize the metrics store."""
        # Basic request metrics
        self.request_count = 0
        self.error_count = 0
        self.request_duration_sum = 0.0
        self.request_duration_count = 0

        # HTTP metrics
        self.requests_by_path: Dict[str, int] = {}
        self.requests_by_method: Dict[str, int] = {}
        self.requests_by_status: Dict[int, int] = {}
        self.errors_by_type: Dict[str, int] = {}

        # Enhanced LLM metrics
        self.llm_requests: Dict[str, int] = {}  # by provider
        self.llm_models: Dict[str, int] = {}  # by model
        self.llm_tokens_input: Dict[str, int] = {}  # by provider/model
        self.llm_tokens_output: Dict[str, int] = {}  # by provider/model
        self.llm_costs: Dict[str, float] = {}  # by provider/model

        # Timing metrics
        self.llm_durations: Dict[str, List[float]] = {}  # by provider/model
        self.llm_time_to_first_token: Dict[str, List[float]] = {}  # by provider/model
        self.llm_time_per_token: Dict[str, List[float]] = {}  # by provider/model

        # Error tracking
        self.llm_errors: Dict[
            str, Dict[str, int]
        ] = {}  # by provider/model -> error type
        self.llm_rate_limits: Dict[str, int] = {}  # by provider/model
        self.llm_structured_success: Dict[str, int] = {}  # by provider/model
        self.llm_structured_failures: Dict[str, int] = {}  # by provider/model

        # Batch processing metrics
        self.batch_sizes: List[int] = []
        self.batch_durations: List[float] = []
        self.batch_success_rate: float = 0.0

        # Detailed request history (last 1000 requests)
        self.request_history: List[LLMRequestMetrics] = []
        self.max_history_size = 1000

        # Thread safety
        self.lock = threading.Lock()

    def clear(self) -> None:
        """Clear all metrics."""
        with self.lock:
            # Reset basic request metrics
            self.request_count = 0
            self.error_count = 0
            self.request_duration_sum = 0.0
            self.request_duration_count = 0

            # Clear HTTP metrics
            self.requests_by_path.clear()
            self.requests_by_method.clear()
            self.requests_by_status.clear()
            self.errors_by_type.clear()

            # Clear LLM metrics
            self.llm_requests.clear()
            self.llm_models.clear()
            self.llm_tokens_input.clear()
            self.llm_tokens_output.clear()
            self.llm_costs.clear()

            # Clear timing metrics
            self.llm_durations.clear()
            self.llm_time_to_first_token.clear()
            self.llm_time_per_token.clear()

            # Clear error tracking
            self.llm_errors.clear()
            self.llm_rate_limits.clear()
            self.llm_structured_success.clear()
            self.llm_structured_failures.clear()

            # Reset batch metrics
            self.batch_sizes.clear()
            self.batch_durations.clear()
            self.batch_success_rate = 0.0

            # Clear request history
            self.request_history.clear()

    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate P50, P90, P95, P99 percentiles for a list of values."""
        if not values:
            return {}

        sorted_values = sorted(values)
        n = len(sorted_values)

        def get_percentile(p: float) -> float:
            index = int(p * n)
            return sorted_values[index]

        return {
            "p50": get_percentile(0.5),
            "p90": get_percentile(0.9),
            "p95": get_percentile(0.95),
            "p99": get_percentile(0.99),
        }

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
                self.requests_by_method[method] = (
                    self.requests_by_method.get(method, 0) + 1
                )

            if path:
                self.requests_by_path[path] = self.requests_by_path.get(path, 0) + 1

            if status_code:
                self.requests_by_status[status_code] = (
                    self.requests_by_status.get(status_code, 0) + 1
                )

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
                self.errors_by_type[error_type] = (
                    self.errors_by_type.get(error_type, 0) + 1
                )

    def record_llm_request(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration: float,
        time_to_first_token: float,
        time_per_token: float,
        cost: float,
        structured: bool = False,
        success: bool = True,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Record detailed metrics for an LLM request.

        Args:
            provider: The LLM provider name
            model: The model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            duration: Request duration in seconds
            time_to_first_token: Time to receive first token in seconds
            time_per_token: Average time per token in seconds
            cost: Cost of the request
            structured: Whether the request was for structured output
            success: Whether the request was successful
            error_type: Type of error if request failed
        """
        with self.lock:
            # Track by provider
            provider_key = provider
            self.llm_requests[provider_key] = self.llm_requests.get(provider_key, 0) + 1
            self.llm_tokens_input[provider_key] = (
                self.llm_tokens_input.get(provider_key, 0) + input_tokens
            )
            self.llm_tokens_output[provider_key] = (
                self.llm_tokens_output.get(provider_key, 0) + output_tokens
            )
            self.llm_costs[provider_key] = self.llm_costs.get(provider_key, 0.0) + cost

            # Track by model
            model_key = f"{provider}:{model}"
            self.llm_models[model_key] = self.llm_models.get(model_key, 0) + 1
            self.llm_tokens_input[model_key] = (
                self.llm_tokens_input.get(model_key, 0) + input_tokens
            )
            self.llm_tokens_output[model_key] = (
                self.llm_tokens_output.get(model_key, 0) + output_tokens
            )
            self.llm_costs[model_key] = self.llm_costs.get(model_key, 0.0) + cost

            # Track timing metrics
            self.llm_durations.setdefault(model_key, []).append(duration)
            self.llm_time_to_first_token.setdefault(model_key, []).append(
                time_to_first_token
            )
            self.llm_time_per_token.setdefault(model_key, []).append(time_per_token)

            # Track structured requests
            if structured:
                if success:
                    self.llm_structured_success[model_key] = (
                        self.llm_structured_success.get(model_key, 0) + 1
                    )
                else:
                    self.llm_structured_failures[model_key] = (
                        self.llm_structured_failures.get(model_key, 0) + 1
                    )

            # Track errors
            if error_type:
                self.llm_errors.setdefault(model_key, {})
                self.llm_errors[model_key][error_type] = (
                    self.llm_errors[model_key].get(error_type, 0) + 1
                )

            # Record detailed metrics
            metrics = LLMRequestMetrics(
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration=duration,
                time_to_first_token=time_to_first_token,
                time_per_token=time_per_token,
                cost=cost,
                structured=structured,
                timestamp=datetime.now(),
                success=success,
                error_type=error_type,
            )
            self.request_history.append(metrics)
            if len(self.request_history) > self.max_history_size:
                self.request_history.pop(0)

    def record_batch_metrics(
        self,
        batch_size: int,
        duration: float,
        success_count: int,
        total_count: int,
    ) -> None:
        """
        Record metrics for batch processing.

        Args:
            batch_size: Number of requests in the batch
            duration: Total processing duration
            success_count: Number of successful requests
            total_count: Total number of requests
        """
        with self.lock:
            self.batch_sizes.append(batch_size)
            self.batch_durations.append(duration)
            self.batch_success_rate = (
                success_count / total_count if total_count > 0 else 0.0
            )

    def record_rate_limit(self, provider: str, model: str) -> None:
        """
        Record a rate limit event.

        Args:
            provider: The LLM provider name
            model: The model name
        """
        with self.lock:
            key = f"{provider}:{model}"
            self.llm_rate_limits[key] = self.llm_rate_limits.get(key, 0) + 1

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
                },
                "llm": {
                    "providers": {
                        provider: {
                            "requests": self.llm_requests.get(provider, 0),
                            "input_tokens": self.llm_tokens_input.get(provider, 0),
                            "output_tokens": self.llm_tokens_output.get(provider, 0),
                            "cost": self.llm_costs.get(provider, 0.0),
                        }
                        for provider in set(
                            key.split(":")[0] for key in self.llm_models.keys()
                        )
                    },
                    "models": {
                        model: {
                            "requests": self.llm_models.get(model, 0),
                            "input_tokens": self.llm_tokens_input.get(model, 0),
                            "output_tokens": self.llm_tokens_output.get(model, 0),
                            "cost": self.llm_costs.get(model, 0.0),
                            "timing": {
                                "total": {
                                    "average": statistics.mean(
                                        self.llm_durations.get(model, [])
                                    )
                                    if self.llm_durations.get(model)
                                    else 0,
                                    "percentiles": self._calculate_percentiles(
                                        self.llm_durations.get(model, [])
                                    ),
                                },
                                "time_to_first_token": {
                                    "average": statistics.mean(
                                        self.llm_time_to_first_token.get(model, [])
                                    )
                                    if self.llm_time_to_first_token.get(model)
                                    else 0,
                                    "percentiles": self._calculate_percentiles(
                                        self.llm_time_to_first_token.get(model, [])
                                    ),
                                },
                                "time_per_token": {
                                    "average": statistics.mean(
                                        self.llm_time_per_token.get(model, [])
                                    )
                                    if self.llm_time_per_token.get(model)
                                    else 0,
                                    "percentiles": self._calculate_percentiles(
                                        self.llm_time_per_token.get(model, [])
                                    ),
                                },
                            },
                            "structured_success": self.llm_structured_success.get(
                                model, 0
                            ),
                            "structured_failures": self.llm_structured_failures.get(
                                model, 0
                            ),
                            "errors": self.llm_errors.get(model, {}),
                            "rate_limits": self.llm_rate_limits.get(model, 0),
                        }
                        for model in self.llm_models.keys()
                    },
                },
                "batch_processing": {
                    "average_batch_size": (
                        sum(self.batch_sizes) / len(self.batch_sizes)
                        if self.batch_sizes
                        else 0
                    ),
                    "average_duration": (
                        sum(self.batch_durations) / len(self.batch_durations)
                        if self.batch_durations
                        else 0
                    ),
                    "success_rate": self.batch_success_rate,
                },
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
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost: float = 0.0,
    structured: bool = False,
) -> ContextManager[None]:
    """
    Context manager for recording LLM request metrics.

    Args:
        provider: The LLM provider name
        model: The model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost: Cost of the request
        structured: Whether the request was for structured output

    Yields:
        None
    """
    start_time = time.time()
    first_token_time = None
    success = True
    error_type = None

    try:
        yield
    except Exception as e:
        success = False
        error_type = type(e).__name__
        raise
    finally:
        duration = time.time() - start_time
        time_to_first_token = first_token_time - start_time if first_token_time else 0
        time_per_token = duration / output_tokens if output_tokens > 0 else 0

        _metrics_store.record_llm_request(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration=duration,
            time_to_first_token=time_to_first_token,
            time_per_token=time_per_token,
            cost=cost,
            structured=structured,
            success=success,
            error_type=error_type,
        )


def record_batch_metrics(
    batch_size: int,
    duration: float,
    success_count: int,
    total_count: int,
) -> None:
    """
    Record metrics for batch processing.

    Args:
        batch_size: Number of requests in the batch
        duration: Total processing duration
        success_count: Number of successful requests
        total_count: Total number of requests
    """
    _metrics_store.record_batch_metrics(
        batch_size, duration, success_count, total_count
    )


def record_rate_limit(provider: str, model: str) -> None:
    """
    Record a rate limit event.

    Args:
        provider: The LLM provider name
        model: The model name
    """
    _metrics_store.record_rate_limit(provider, model)


def record_first_token(provider: str, model: str) -> None:
    """
    Record the time when the first token is received.
    This should be called when the first token is received from the LLM.

    Args:
        provider: The LLM provider name
        model: The model name
    """
    global first_token_time
    first_token_time = time.time()
