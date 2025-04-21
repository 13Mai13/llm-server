import time
import threading
from src.monitoring.tracer import Tracer, get_tracer, trace_span, Span


def test_span_creation():
    """Test basic span creation and properties."""
    tracer = Tracer()
    root_span = tracer.start_trace("test_span")

    assert root_span.name == "test_span"
    assert root_span.trace_id is not None
    assert root_span.parent_id is None
    assert root_span.start_time is not None
    assert root_span.end_time is None
    assert root_span.tags == {}
    assert root_span.events == []


def test_span_tags_and_events():
    """Test adding tags and events to spans."""
    tracer = Tracer()
    root_span = tracer.start_trace("test_span")

    root_span.set_tag("key", "value")
    assert root_span.tags["key"] == "value"

    root_span.add_event("test_event", data="test_data")
    assert len(root_span.events) == 1
    assert root_span.events[0]["name"] == "test_event"
    assert root_span.events[0]["data"] == "test_data"


def test_span_duration():
    """Test span duration calculation."""
    tracer = Tracer()
    root_span = tracer.start_trace("test_span")
    time.sleep(0.1)
    root_span.finish()

    assert root_span.duration >= 0.1
    assert root_span.end_time is not None


def test_tracer_basic():
    """Test basic tracer functionality."""
    tracer = Tracer()

    # Test starting a trace
    root_span = tracer.start_trace("root_span")
    assert root_span.name == "root_span"
    assert root_span.parent_id is None

    # Test starting a child span
    child_span = tracer.start_span("child_span")
    assert child_span.name == "child_span"
    assert child_span.parent_id == root_span.span_id
    assert child_span.trace_id == root_span.trace_id


def test_tracer_active_span():
    """Test active span tracking."""
    tracer = Tracer()

    # Test getting active span when none exists
    assert tracer.get_active_span() is None

    # Test active span after starting a trace
    root_span = tracer.start_trace("root_span")
    assert tracer.get_active_span() == root_span

    # Test active span after starting a child span
    child_span = tracer.start_span("child_span")
    assert tracer.get_active_span() == child_span

    # Test active span after finishing a span
    tracer.finish_span(child_span)
    assert tracer.get_active_span() == root_span


def test_tracer_context_manager():
    """Test tracer context manager functionality."""
    tracer = get_tracer()
    tracer.clear()  # Clear any existing spans

    # Start a trace first
    root_span = tracer.start_trace("root_span")

    # Test context manager with active span
    with trace_span("test_span") as span:
        assert span.name == "test_span"
        active_span = tracer.get_active_span()
        assert active_span is not None
        assert active_span.name == span.name
        assert active_span.span_id == span.span_id
        assert span.parent_id == root_span.span_id

    # After context manager, active span should be root_span
    active_span = tracer.get_active_span()
    assert active_span is not None
    assert active_span.name == "root_span"
    assert active_span.span_id == root_span.span_id

    # Test context manager without active span
    tracer.clear()
    with trace_span("new_span") as span:
        assert span.name == "new_span"
        active_span = tracer.get_active_span()
        assert active_span is not None
        assert active_span.name == span.name
        assert active_span.span_id == span.span_id
        assert span.parent_id is None

    # After context manager, no active span
    assert tracer.get_active_span() is None


def test_tracer_thread_safety():
    """Test tracer thread safety."""
    Tracer()
    results = []

    def worker():
        with trace_span("worker_span") as span:
            time.sleep(0.1)
            results.append(span.span_id)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Each thread should have its own span
    assert len(set(results)) == 5


def test_tracer_clear():
    """Test clearing the tracer."""
    tracer = Tracer()

    # Create some spans
    root_span = tracer.start_trace("root_span")
    child_span = tracer.start_span("child_span")

    # Clear the tracer
    tracer.clear()

    # Verify spans are cleared
    assert tracer.get_span(root_span.span_id) is None
    assert tracer.get_span(child_span.span_id) is None
    assert tracer.get_active_span() is None
    assert len(tracer.get_trace(root_span.trace_id)) == 0


class TestTracer:
    def test_basic_tracing(self):
        """Test basic tracing functionality."""
        tracer = Tracer()
        tracer.start_trace("test_span")

        # Test creating and ending a span
        span = tracer.start_span("test_span")
        assert isinstance(span, Span)
        assert span.name == "test_span"
        assert span.start_time is not None
        assert span.end_time is None

        span.finish()
        assert span.end_time is not None
        assert span.duration > 0

    def test_nested_spans(self):
        """Test nested span functionality."""
        tracer = Tracer()
        root_span = tracer.start_trace("parent")

        # Test creating nested spans
        child = tracer.start_span("child")

        assert child.parent_id == root_span.span_id
        assert child.trace_id == root_span.trace_id

        child.finish()
        root_span.finish()

        assert child.end_time is not None
        assert root_span.end_time is not None
        assert root_span.duration >= child.duration

    def test_span_attributes(self):
        """Test span attribute functionality."""
        tracer = Tracer()
        tracer.start_trace("test_span")

        # Test setting and getting attributes
        span = tracer.start_span("test_span")
        span.set_tag("key", "value")
        span.set_tag("number", 42)

        assert span.tags["key"] == "value"
        assert span.tags["number"] == 42

        span.finish()

    def test_span_events(self):
        """Test span event functionality."""
        tracer = Tracer()
        tracer.start_trace("test_span")

        # Test adding events
        span = tracer.start_span("test_span")
        span.add_event("test_event", key="value")

        assert len(span.events) == 1
        event = span.events[0]
        assert event["name"] == "test_event"
        assert event["key"] == "value"

        span.finish()

    def test_span_status(self):
        """Test span status functionality."""
        tracer = Tracer()
        tracer.start_trace("test_span")

        # Test setting status
        span = tracer.start_span("test_span")
        span.set_tag("status", "OK")
        assert span.tags["status"] == "OK"

        span.set_tag("status", "ERROR")
        span.set_tag("error.message", "Test error")
        assert span.tags["status"] == "ERROR"
        assert span.tags["error.message"] == "Test error"

        span.finish()

    def test_tracer_context(self):
        """Test tracer context management."""
        tracer = Tracer()
        tracer.start_trace("test_span")

        # Test context management
        with trace_span("test_span") as span:
            assert span.end_time is None
            assert "status" not in span.tags

        assert span.end_time is not None
