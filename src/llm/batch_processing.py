import logging
import asyncio
from typing import (
    List,
    Optional,
    Callable,
    Awaitable,
    TypeVar,
    Generic,
    Tuple,
)
from dataclasses import dataclass
import time


logger = logging.getLogger(__name__)

# Generic type for request and response
T = TypeVar("T")
R = TypeVar("R")


@dataclass
class BatchItem(Generic[T, R]):
    """
    Represents an item in a batch.

    This class holds a request, a future for the response, and metadata
    about the request.
    """

    request: T
    future: asyncio.Future
    timestamp: float
    timeout: float

    def is_expired(self) -> bool:
        """Check if the request has expired."""
        return time.time() - self.timestamp > self.timeout


class BatchManager(Generic[T, R]):
    """
    Manages batches of requests to improve throughput.

    This class collects incoming requests into batches and processes them
    together to reduce overhead.
    """

    def __init__(
        self,
        batch_processor: Callable[[List[T]], Awaitable[List[R]]],
        max_batch_size: int = 10,
        max_wait_time: float = 0.1,
        request_timeout: float = 30.0,
    ):
        """
        Initialize a batch manager.

        Args:
            batch_processor: Function to process a batch of requests
            max_batch_size: Maximum number of requests in a batch
            max_wait_time: Maximum time to wait for a batch to fill up
            request_timeout: Maximum time to wait for a request to complete
        """
        self.batch_processor = batch_processor
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.request_timeout = request_timeout
        self.queue: List[BatchItem[T, R]] = []
        self.lock = asyncio.Lock()
        self.batch_task: Optional[asyncio.Task] = None
        self.running = False
        logger.info(
            f"Created batch manager with max batch size {max_batch_size}, "
            f"max wait time {max_wait_time}s, request timeout {request_timeout}s"
        )

    async def start(self) -> None:
        """Start the batch manager."""
        if self.running:
            return

        self.running = True
        self.batch_task = asyncio.create_task(self._process_batches())
        logger.info("Started batch manager")

    async def stop(self) -> None:
        """Stop the batch manager."""
        if not self.running:
            return

        self.running = False
        if self.batch_task:
            self.batch_task.cancel()
            try:
                await self.batch_task
            except asyncio.CancelledError:
                pass
            self.batch_task = None

        # Cancel all pending requests
        async with self.lock:
            for item in self.queue:
                if not item.future.done():
                    item.future.cancel()
            self.queue.clear()

        logger.info("Stopped batch manager")

    async def add_request(self, request: T) -> R:
        """
        Add a request to the batch.

        Args:
            request: The request to add

        Returns:
            R: The response

        Raises:
            TimeoutError: If the request times out
            asyncio.CancelledError: If the request is cancelled
        """
        # Create a future for the response
        future = asyncio.get_event_loop().create_future()

        # Create a batch item
        item = BatchItem(
            request=request,
            future=future,
            timestamp=time.time(),
            timeout=self.request_timeout,
        )

        # Add the item to the queue
        async with self.lock:
            self.queue.append(item)

        try:
            # Wait for the response
            return await future
        except asyncio.CancelledError:
            # If the future is cancelled, remove the item from the queue
            async with self.lock:
                if item in self.queue:
                    self.queue.remove(item)
            raise

    async def _process_batches(self) -> None:
        """Process batches of requests."""
        while self.running:
            try:
                # Wait for the batch to fill up or for the max wait time to elapse
                batch_ready_event = asyncio.Event()
                check_batch_task = asyncio.create_task(
                    self._check_batch_ready(batch_ready_event)
                )

                try:
                    # Wait for the batch to be ready
                    await asyncio.wait_for(
                        batch_ready_event.wait(),
                        timeout=self.max_wait_time,
                    )
                except asyncio.TimeoutError:
                    # Timeout elapsed, process the batch anyway
                    pass
                finally:
                    check_batch_task.cancel()
                    try:
                        await check_batch_task
                    except asyncio.CancelledError:
                        pass

                # Get the batch
                batch, items = await self._get_batch()

                # If there are no items in the batch, wait and try again
                if not items:
                    await asyncio.sleep(0.01)
                    continue

                # Process the batch
                try:
                    responses = await self.batch_processor(batch)

                    # Set the results
                    for item, response in zip(items, responses):
                        if not item.future.done():
                            item.future.set_result(response)

                except Exception as e:
                    logger.error(f"Error processing batch: {str(e)}")

                    # Set the exception for all items
                    for item in items:
                        if not item.future.done():
                            item.future.set_exception(e)

            except Exception as e:
                logger.error(f"Error in batch manager: {str(e)}")
                await asyncio.sleep(0.1)

    async def _check_batch_ready(self, event: asyncio.Event) -> None:
        """
        Check if a batch is ready to be processed.

        A batch is ready if it has reached the maximum size.

        Args:
            event: Event to set when a batch is ready
        """
        while self.running:
            async with self.lock:
                if len(self.queue) >= self.max_batch_size:
                    event.set()
                    return

            await asyncio.sleep(0.01)

    async def _get_batch(self) -> Tuple[List[T], List[BatchItem[T, R]]]:
        """
        Get a batch of requests to process.

        Returns:
            Tuple[List[T], List[BatchItem[T, R]]]: The batch of requests and the batch items
        """
        batch: List[T] = []
        items: List[BatchItem[T, R]] = []

        async with self.lock:
            # Get up to max_batch_size items from the queue
            batch_items = self.queue[: self.max_batch_size]
            self.queue = self.queue[self.max_batch_size :]

            # Filter out expired items
            current_time = time.time()
            for item in batch_items:
                if current_time - item.timestamp > item.timeout:
                    # Item has expired, set a timeout error
                    if not item.future.done():
                        item.future.set_exception(
                            TimeoutError(f"Request timed out after {item.timeout}s")
                        )
                else:
                    # Item is still valid, add it to the batch
                    batch.append(item.request)
                    items.append(item)

        return batch, items


# TODO: Remove this when endpoint is implemented
# Example usage:
#
# async def process_llm_batch(requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     """Process a batch of LLM requests."""
#     # Implementation would call the LLM API with the batch
#     responses = []
#     for request in requests:
#         # This is where you'd actually call the LLM API
#         responses.append({"result": f"Response for {request['prompt']}"})
#     return responses
#
#
# # Create a batch manager
# batch_manager = BatchManager(
#     batch_processor=process_llm_batch,
#     max_batch_size=settings.BATCH_SIZE,
#     max_wait_time=0.1,
#     request_timeout=settings.REQUEST_TIMEOUT,
# )
#
# # Start the batch manager
# await batch_manager.start()
#
# # Add a request to the batch
# response = await batch_manager.add_request({"prompt": "Hello, world!"})
#
# # Stop the batch manager when done
# await batch_manager.stop()
