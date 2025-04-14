import asyncio
import pytest
from unittest.mock import AsyncMock, patch
import time
from typing import List

from src.llm.batch_processing import BatchManager, BatchItem


@pytest.fixture
def mock_batch_processor():
    """Create a mock batch processor function."""

    async def processor(batch: List[str]) -> List[str]:
        return [f"processed_{item}" for item in batch]

    return AsyncMock(side_effect=processor)


@pytest.mark.asyncio
async def test_batch_manager_init(mock_batch_processor):
    """Test BatchManager initialization."""
    manager = BatchManager(
        batch_processor=mock_batch_processor,
        max_batch_size=5,
        max_wait_time=0.2,
        request_timeout=10.0,
    )

    assert manager.batch_processor == mock_batch_processor
    assert manager.max_batch_size == 5
    assert manager.max_wait_time == 0.2
    assert manager.request_timeout == 10.0
    assert manager.queue == []
    assert manager.batch_task is None
    assert not manager.running


@pytest.mark.asyncio
async def test_batch_manager_start_stop(mock_batch_processor):
    """Test starting and stopping the BatchManager."""
    manager = BatchManager(
        batch_processor=mock_batch_processor, max_batch_size=5, max_wait_time=0.2
    )

    # Start the manager
    await manager.start()
    assert manager.running is True
    assert manager.batch_task is not None

    # Starting again should be a no-op
    await manager.start()
    assert manager.running is True

    # Stop the manager
    await manager.stop()
    assert manager.running is False
    assert manager.batch_task is None

    # Stopping again should be a no-op
    await manager.stop()
    assert manager.running is False


@pytest.mark.asyncio
async def test_add_request_single(mock_batch_processor):
    """Test adding a single request."""
    manager = BatchManager(
        batch_processor=mock_batch_processor, max_batch_size=5, max_wait_time=0.2
    )

    await manager.start()

    try:
        # Add a request
        result = await manager.add_request("test_request")

        # Verify the result
        assert result == "processed_test_request"

        # Verify the processor was called with the correct batch
        mock_batch_processor.assert_called_once_with(["test_request"])
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_add_request_multiple(mock_batch_processor):
    """Test adding multiple requests."""
    manager = BatchManager(
        batch_processor=mock_batch_processor, max_batch_size=3, max_wait_time=1.0
    )

    await manager.start()

    try:
        # Add multiple requests concurrently
        tasks = [
            asyncio.create_task(manager.add_request(f"request_{i}")) for i in range(3)
        ]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        # Verify the results
        assert results == [
            "processed_request_0",
            "processed_request_1",
            "processed_request_2",
        ]

        # Verify the processor was called with the correct batch
        mock_batch_processor.assert_called_once()
        actual_batch = mock_batch_processor.call_args[0][0]
        assert sorted(actual_batch) == sorted([f"request_{i}" for i in range(3)])
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_batch_wait_time(mock_batch_processor):
    """Test that a batch is processed after max_wait_time."""
    manager = BatchManager(
        batch_processor=mock_batch_processor,
        max_batch_size=10,  # Large batch size to ensure timeout triggers first
        max_wait_time=0.1,  # Short wait time for testing
    )

    await manager.start()

    try:
        # Add a single request
        start_time = time.time()
        result = await manager.add_request("test_request")
        elapsed_time = time.time() - start_time

        # Verify the result
        assert result == "processed_test_request"

        # Verify that we waited at least max_wait_time
        assert elapsed_time >= 0.1

        # Verify the processor was called with the correct batch
        mock_batch_processor.assert_called_once_with(["test_request"])
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_batch_max_size(mock_batch_processor):
    """Test that a batch is processed when it reaches max_batch_size."""
    manager = BatchManager(
        batch_processor=mock_batch_processor,
        max_batch_size=3,
        max_wait_time=10.0,  # Long wait time to ensure batch size triggers first
    )

    # Patch the _check_batch_ready method to record when it's called
    original_check = manager._check_batch_ready
    check_called = asyncio.Event()

    async def patched_check(event):
        check_called.set()
        await original_check(event)

    manager._check_batch_ready = patched_check

    await manager.start()

    try:
        # Add multiple requests concurrently
        tasks = [
            asyncio.create_task(manager.add_request(f"request_{i}")) for i in range(3)
        ]

        # Wait for the check to be called
        await asyncio.wait_for(check_called.wait(), timeout=1.0)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        # Verify the results
        assert sorted(results) == sorted(
            ["processed_request_0", "processed_request_1", "processed_request_2"]
        )

        # Verify the processor was called with the correct batch
        mock_batch_processor.assert_called_once()
        actual_batch = mock_batch_processor.call_args[0][0]
        assert sorted(actual_batch) == sorted([f"request_{i}" for i in range(3)])
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_request_timeout(mock_batch_processor):
    """Test that a request times out after request_timeout."""
    # Create a manager with a short request timeout
    manager = BatchManager(
        batch_processor=mock_batch_processor,
        max_batch_size=5,
        max_wait_time=0.1,
        request_timeout=0.1,
    )

    # Create a request that's already expired
    expired_item = BatchItem(
        request="expired_request",
        future=asyncio.get_event_loop().create_future(),
        timestamp=time.time() - 1.0,  # Set timestamp in the past
        timeout=0.1,
    )

    # Add the item to the queue
    manager.queue.append(expired_item)

    await manager.start()

    try:
        # Wait for the batch to be processed
        await asyncio.sleep(0.2)

        # Verify the future was completed with a TimeoutError
        assert expired_item.future.done()
        with pytest.raises(TimeoutError):
            await expired_item.future
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_processor_error(mock_batch_processor):
    """Test handling of errors from the batch processor."""
    # Configure the mock processor to raise an exception
    error = ValueError("Test error")
    mock_batch_processor.side_effect = error

    manager = BatchManager(
        batch_processor=mock_batch_processor, max_batch_size=2, max_wait_time=0.1
    )

    await manager.start()

    try:
        # Add a request
        with pytest.raises(ValueError, match="Test error"):
            await manager.add_request("test_request")

        # Verify the processor was called
        mock_batch_processor.assert_called_once_with(["test_request"])
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_cancellation():
    """Test cancellation of requests."""

    # Create a processor that never completes
    async def slow_processor(batch):
        await asyncio.sleep(10.0)
        return batch

    manager = BatchManager(
        batch_processor=slow_processor, max_batch_size=2, max_wait_time=0.1
    )

    await manager.start()

    try:
        # Start a request
        task = asyncio.create_task(manager.add_request("test_request"))

        # Wait a bit for the request to be queued
        await asyncio.sleep(0.1)

        # Cancel the task
        task.cancel()

        # Verify the task is cancelled
        with pytest.raises(asyncio.CancelledError):
            await task

        # Verify the queue is empty (request was removed)
        assert len(manager.queue) == 0
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_process_batches_error_handling():
    """Test error handling in the _process_batches method."""
    # Create a processor that works once then fails
    call_count = 0

    async def failing_processor(batch):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [f"processed_{item}" for item in batch]
        else:
            raise ValueError("Processor error")

    manager = BatchManager(
        batch_processor=failing_processor, max_batch_size=1, max_wait_time=0.1
    )

    # Mock logger to capture errors
    with patch("src.llm.batch_processing.logger") as mock_logger:
        await manager.start()

        try:
            # First request should succeed
            result1 = await manager.add_request("request_1")
            assert result1 == "processed_request_1"

            # Second request should fail but not crash the manager
            with pytest.raises(ValueError, match="Processor error"):
                await manager.add_request("request_2")

            # Verify error was logged
            mock_logger.error.assert_called_with(
                "Error processing batch: Processor error"
            )

            # Third request should restart the process and fail again
            with pytest.raises(ValueError, match="Processor error"):
                await manager.add_request("request_3")
        finally:
            await manager.stop()
