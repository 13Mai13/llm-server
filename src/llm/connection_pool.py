import logging
import asyncio
from typing import Dict, List, Set, Optional
import httpx
from contextlib import asynccontextmanager

from src.config import settings
from src.llm.providers import get_llm_providers, initialize_providers


logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    Connection pool for managing HTTP connections to LLM providers.

    This class maintains a pool of HTTP clients and manages their lifecycle.
    It provides methods for acquiring and releasing connections.
    """

    def __init__(self, provider_name: str, max_connections: int = 10):
        """
        Initialize a connection pool for a provider.

        Args:
            provider_name: Name of the LLM provider
            max_connections: Maximum number of connections in the pool
        """
        self.provider_name = provider_name
        self.max_connections = max_connections
        self.connections: List[httpx.AsyncClient] = []
        self.available_connections: Set[httpx.AsyncClient] = set()
        self.semaphore = asyncio.Semaphore(max_connections)
        self.lock = asyncio.Lock()
        logger.info(
            f"Created connection pool for {provider_name} with {max_connections} max connections"
        )

    async def initialize(self, base_url: str, headers: Dict[str, str]) -> None:
        """
        Initialize the connection pool with pre-created connections.

        Args:
            base_url: Base URL for the provider API
            headers: Headers to include in all requests
        """
        async with self.lock:
            # Create initial connections
            for _ in range(self.max_connections):
                client = httpx.AsyncClient(
                    base_url=base_url,
                    headers=headers,
                    timeout=httpx.Timeout(
                        connect=settings.CONNECTION_TIMEOUT,
                        read=settings.REQUEST_TIMEOUT,
                        write=settings.REQUEST_TIMEOUT,
                        pool=settings.KEEPALIVE_TIMEOUT,
                    ),
                    limits=httpx.Limits(
                        max_keepalive_connections=self.max_connections,
                        max_connections=self.max_connections * 2,
                        keepalive_expiry=settings.KEEPALIVE_TIMEOUT,
                    ),
                )
                self.connections.append(client)
                self.available_connections.add(client)

            logger.info(
                f"Initialized {len(self.connections)} connections for {self.provider_name}"
            )

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool.

        Returns:
            AsyncContextManager: Context manager that yields a connection and releases it when done
        """
        async with self.semaphore:
            async with self.lock:
                if not self.available_connections:
                    logger.warning(
                        f"No available connections for {self.provider_name}, creating a new one"
                    )
                    client = httpx.AsyncClient(
                        timeout=httpx.Timeout(60.0),
                    )
                    self.connections.append(client)
                else:
                    client = self.available_connections.pop()

            try:
                # Yield the connection to the caller
                yield client
            finally:
                # Return the connection to the pool
                async with self.lock:
                    if (
                        client in self.connections
                    ):  # It might have been removed if closed
                        self.available_connections.add(client)

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self.lock:
            for client in self.connections:
                await client.aclose()

            self.connections.clear()
            self.available_connections.clear()

            logger.info(f"Closed all connections for {self.provider_name}")


# Global dictionary of connection pools by provider
_connection_pools: Dict[str, ConnectionPool] = {}


def get_connection_pool(provider_name: str) -> Optional[ConnectionPool]:
    """
    Get a connection pool for a provider.

    Args:
        provider_name: Name of the LLM provider

    Returns:
        Optional[ConnectionPool]: The connection pool, or None if the provider is not registered
    """
    return _connection_pools.get(provider_name)


@asynccontextmanager
async def get_connection(provider_name: str):
    """
    Get a connection for a provider.

    Args:
        provider_name: Name of the LLM provider

    Yields:
        httpx.AsyncClient: The HTTP client

    Raises:
        ValueError: If the provider is not registered
    """
    pool = get_connection_pool(provider_name)
    if not pool:
        raise ValueError(f"Provider {provider_name} not registered")

    async with pool.acquire() as client:
        yield client


async def setup_connection_pools() -> None:
    """Set up connection pools for all registered providers."""
    await initialize_providers()
    providers = get_llm_providers()

    for provider_name, provider in providers.items():
        try:
            base_url = getattr(provider, "base_url", None)
            api_key = getattr(provider, "api_key", None)

            if not base_url or not api_key:
                logger.warning(
                    f"Could not set up connection pool for {provider_name}: missing base_url or api_key"
                )
                continue

            headers = {"Authorization": f"Bearer {api_key}"}

            pool = ConnectionPool(
                provider_name=provider_name,
                max_connections=settings.MAX_CONNECTIONS,
            )

            # Initialize the pool
            await pool.initialize(
                base_url=base_url,
                headers=headers,
            )

            # Register the pool
            _connection_pools[provider_name] = pool

            logger.info(f"Set up connection pool for {provider_name}")

        except Exception as e:
            logger.error(
                f"Error setting up connection pool for {provider_name}: {str(e)}"
            )

    logger.info(f"Set up {len(_connection_pools)} connection pools")


async def close_connection_pools() -> None:
    """Close all connection pools."""
    for pool in _connection_pools.values():
        await pool.close()

    _connection_pools.clear()
    logger.info("Closed all connection pools")
