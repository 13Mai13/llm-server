import pytest
import threading
from src.monitoring.metrics import (
    get_metrics_store,
    increment_request_count,
    record_request_metrics,
    record_batch_metrics,
    record_rate_limit,
)


class TestMetricsStore:
    def setup_method(self):
        """Clear metrics store before each test"""
        self.store = get_metrics_store()
        self.store.clear()

    def test_basic_metrics(self):
        """Test basic request metrics"""
        increment_request_count("GET", "/test", 200, 1.0)
        increment_request_count("POST", "/test", 201, 2.0)

        metrics = self.store.get_metrics()
        assert metrics["requests"]["total"] == 2
        assert metrics["requests"]["by_method"]["GET"] == 1
        assert metrics["requests"]["by_method"]["POST"] == 1
        assert metrics["requests"]["by_path"]["/test"] == 2
        assert metrics["requests"]["by_status"][200] == 1
        assert metrics["requests"]["by_status"][201] == 1
        assert metrics["requests"]["average_duration"] == 1.5

    def test_llm_metrics(self):
        """Test LLM metrics recording"""
        with record_request_metrics(
            provider="test_provider",
            model="test_model",
            input_tokens=100,
            output_tokens=50,
            cost=0.1,
            structured=True,
        ):
            pass

        metrics = self.store.get_metrics()
        model_key = "test_provider:test_model"
        assert metrics["llm"]["providers"]["test_provider"]["requests"] == 1
        assert metrics["llm"]["providers"]["test_provider"]["input_tokens"] == 100
        assert metrics["llm"]["providers"]["test_provider"]["output_tokens"] == 50
        assert metrics["llm"]["providers"]["test_provider"]["cost"] == 0.1
        assert metrics["llm"]["models"][model_key]["requests"] == 1
        assert metrics["llm"]["models"][model_key]["input_tokens"] == 100
        assert metrics["llm"]["models"][model_key]["output_tokens"] == 50
        assert metrics["llm"]["models"][model_key]["cost"] == 0.1
        assert metrics["llm"]["models"][model_key]["structured_success"] == 1

    def test_batch_metrics(self):
        """Test batch processing metrics"""
        record_batch_metrics(
            batch_size=10,
            duration=1.0,
            success_count=8,
            total_count=10,
        )

        metrics = self.store.get_metrics()
        assert metrics["batch_processing"]["average_batch_size"] == 10
        assert metrics["batch_processing"]["average_duration"] == 1.0
        assert metrics["batch_processing"]["success_rate"] == 0.8

    def test_rate_limits(self):
        """Test rate limit recording"""
        with record_request_metrics(
            provider="test_provider",
            model="test_model",
            input_tokens=0,
            output_tokens=0,
            cost=0.0,
        ):
            record_rate_limit("test_provider", "test_model")
            record_rate_limit("test_provider", "test_model")

        metrics = self.store.get_metrics()
        model_key = "test_provider:test_model"
        assert metrics["llm"]["models"][model_key]["rate_limits"] == 2

    def test_error_handling(self):
        """Test error recording"""

        class TestError(Exception):
            pass

        with pytest.raises(TestError):
            with record_request_metrics(
                provider="test_provider",
                model="test_model",
                input_tokens=100,
                output_tokens=50,
                cost=0.1,
                structured=True,
            ):
                raise TestError("test error")

        metrics = self.store.get_metrics()
        model_key = "test_provider:test_model"
        assert metrics["llm"]["models"][model_key]["requests"] == 1
        assert metrics["llm"]["models"][model_key]["errors"]["TestError"] == 1
        assert metrics["llm"]["models"][model_key]["structured_failures"] == 1

    def test_thread_safety(self):
        """Test thread safety of metrics store"""

        def record_requests():
            for _ in range(100):
                increment_request_count("GET", "/test", 200, 1.0)

        threads = [threading.Thread(target=record_requests) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        metrics = self.store.get_metrics()
        assert metrics["requests"]["total"] == 1000
        assert metrics["requests"]["by_method"]["GET"] == 1000
        assert metrics["requests"]["by_path"]["/test"] == 1000
        assert metrics["requests"]["by_status"][200] == 1000


# Standalone test functions
def test_batch_metrics():
    """Test batch metrics recording"""
    store = get_metrics_store()
    store.clear()

    record_batch_metrics(
        batch_size=10,
        duration=1.0,
        success_count=8,
        total_count=10,
    )

    metrics = store.get_metrics()
    assert metrics["batch_processing"]["average_batch_size"] == 10
    assert metrics["batch_processing"]["average_duration"] == 1.0
    assert metrics["batch_processing"]["success_rate"] == 0.8


def test_rate_limit_recording():
    """Test rate limit recording"""
    store = get_metrics_store()
    store.clear()

    with record_request_metrics(
        provider="test_provider",
        model="test_model",
        input_tokens=0,
        output_tokens=0,
        cost=0.0,
    ):
        record_rate_limit("test_provider", "test_model")
        record_rate_limit("test_provider", "test_model")

    metrics = store.get_metrics()
    model_key = "test_provider:test_model"
    assert metrics["llm"]["models"][model_key]["rate_limits"] == 2


def test_error_handling():
    """Test error recording"""

    class TestError(Exception):
        pass

    store = get_metrics_store()
    store.clear()

    with pytest.raises(TestError):
        with record_request_metrics(
            provider="test_provider",
            model="test_model",
            input_tokens=100,
            output_tokens=50,
            cost=0.1,
            structured=True,
        ):
            raise TestError("test error")

    metrics = store.get_metrics()
    model_key = "test_provider:test_model"
    assert metrics["llm"]["models"][model_key]["requests"] == 1
    assert metrics["llm"]["models"][model_key]["errors"]["TestError"] == 1
    assert metrics["llm"]["models"][model_key]["structured_failures"] == 1
