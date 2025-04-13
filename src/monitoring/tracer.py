import logging
import time
import uuid
from typing import Dict, Any, Optional, List, ContextManager
from contextlib import contextmanager
import threading



logger = logging.getLogger(__name__)


class Span:
    """
    Represents a span in a trace.

    A span represents a single operation within a trace. It tracks the
    duration of the operation, any tags associated with it, and any
    events that occurred during the operation.
    """

    def __init__(
        self,
        name: str,
        trace_id: str,
        parent_id: Optional[str] = None,
    ):
        """
        Initialize a span.

        Args:
            name: The name of the span
            trace_id: The ID of the trace this span belongs to
            parent_id: The ID of the parent span, if any
        """
        self.name = name
        self.trace_id = trace_id
        self.span_id = str(uuid.uuid4())
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.tags: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []

    def set_tag(self, key: str, value: Any) -> None:
        """
        Set a tag on the span.

        Args:
            key: The tag key
            value: The tag value
        """
        self.tags[key] = value

    def add_event(self, name: str, **kwargs: Any) -> None:
        """
        Add an event to the span.

        Args:
            name: The event name
            **kwargs: Additional event attributes
        """
        self.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                **kwargs,
            }
        )

    def finish(self) -> None:
        """Mark the span as finished and record the end time."""
        self.end_time = time.time()

    @property
    def duration(self) -> float:
        """
        Get the duration of the span in seconds.

        Returns:
            float: The duration in seconds
        """
        if self.end_time is None:
            return time.time() - self.start_time

        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the span to a dictionary.

        Returns:
            Dict[str, Any]: The span as a dictionary
        """
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "tags": self.tags,
            "events": self.events,
        }


class Tracer:
    """
    Distributed tracing system.

    This class provides functionality for tracing requests through the system.
    It allows creating spans to track operations and their durations.

    In a production environment, this would be replaced with a proper
    tracing system like Jaeger or Zipkin.
    """

    def __init__(self):
        """Initialize the tracer."""
        self.spans: Dict[str, Span] = {}
        self.active_spans: Dict[int, List[Span]] = {}
        self.lock = threading.Lock()

    def start_trace(self, name: str) -> Span:
        """
        Start a new trace.

        Args:
            name: The name of the root span

        Returns:
            Span: The root span
        """
        trace_id = str(uuid.uuid4())
        thread_id = threading.get_ident()

        span = Span(name=name, trace_id=trace_id)

        with self.lock:
            self.spans[span.span_id] = span

            if thread_id not in self.active_spans:
                self.active_spans[thread_id] = []

            self.active_spans[thread_id].append(span)

        return span

    def start_span(self, name: str, parent_span: Optional[Span] = None) -> Span:
        """
        Start a new span.

        Args:
            name: The name of the span
            parent_span: The parent span, if any

        Returns:
            Span: The new span

        Raises:
            ValueError: If no parent span is provided and no active spans exist
        """
        thread_id = threading.get_ident()

        # If no parent span is provided, use the current active span
        if parent_span is None:
            with self.lock:
                if (
                    thread_id not in self.active_spans
                    or not self.active_spans[thread_id]
                ):
                    raise ValueError("No active span and no parent span provided")

                parent_span = self.active_spans[thread_id][-1]

        # Create a new span
        span = Span(
            name=name,
            trace_id=parent_span.trace_id,
            parent_id=parent_span.span_id,
        )

        # Register the span
        with self.lock:
            self.spans[span.span_id] = span

            if thread_id not in self.active_spans:
                self.active_spans[thread_id] = []

            self.active_spans[thread_id].append(span)

        return span

    def finish_span(self, span: Span) -> None:
        """
        Finish a span.

        Args:
            span: The span to finish
        """
        span.finish()

        thread_id = threading.get_ident()

        with self.lock:
            if thread_id in self.active_spans and span in self.active_spans[thread_id]:
                self.active_spans[thread_id].remove(span)

    def get_span(self, span_id: str) -> Optional[Span]:
        """
        Get a span by ID.

        Args:
            span_id: The span ID

        Returns:
            Optional[Span]: The span, if found
        """
        return self.spans.get(span_id)

    def get_trace(self, trace_id: str) -> List[Span]:
        """
        Get all spans in a trace.

        Args:
            trace_id: The trace ID

        Returns:
            List[Span]: The spans in the trace
        """
        return [span for span in self.spans.values() if span.trace_id == trace_id]

    def get_active_span(self) -> Optional[Span]:
        """
        Get the currently active span for the current thread.

        Returns:
            Optional[Span]: The active span, if any
        """
        thread_id = threading.get_ident()

        with self.lock:
            if thread_id in self.active_spans and self.active_spans[thread_id]:
                return self.active_spans[thread_id][-1]

        return None

    def clear(self) -> None:
        """Clear all spans."""
        with self.lock:
            self.spans.clear()
            self.active_spans.clear()


# Global tracer
_tracer = Tracer()


def get_tracer() -> Tracer:
    """
    Get the global tracer.

    Returns:
        Tracer: The tracer
    """
    return _tracer


@contextmanager
def trace_span(name: str, parent_span: Optional[Span] = None) -> ContextManager[Span]:
    """
    Context manager for creating and finishing spans.

    Args:
        name: The name of the span
        parent_span: The parent span, if any

    Yields:
        Span: The span
    """
    tracer = get_tracer()

    if parent_span is None:
        try:
            span = tracer.start_span(name)
        except ValueError:
            # No active span, start a new trace
            span = tracer.start_trace(name)
    else:
        span = tracer.start_span(name, parent_span)

    try:
        yield span
    finally:
        tracer.finish_span(span)


def get_active_span() -> Optional[Span]:
    """
    Get the currently active span.

    Returns:
        Optional[Span]: The active span, if any
    """
    return get_tracer().get_active_span()
