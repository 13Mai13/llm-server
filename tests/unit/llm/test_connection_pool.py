import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from src.llm.connection_pool import (
    ConnectionPool,
    get_connection_pool,
    get_connection,
    setup_connection_pools,
    close_connection_pools,
    _connection_pools,
)


@pytest.fixture
def reset_connection_pools():
    """Reset the global connection pools dictionary before and after tests."""
    _connection_pools.clear()
    yield
    _connection_pools.clear()


class TestConnectionPool:
    """Tests for the ConnectionPool class."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test ConnectionPool initialization."""
        pool = ConnectionPool("test_provider", 5)

        assert pool.provider_name == "test_provider"
        assert pool.max_connections == 5
        assert len(pool.connections) == 0
        assert len(pool.available_connections) == 0
        assert isinstance(pool.semaphore, asyncio.Semaphore)
        assert isinstance(pool.lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test initialize method creates connections."""
        pool = ConnectionPool("test_provider", 3)

        # Create unique mock clients for each call
        client_mock1 = MagicMock(spec=httpx.AsyncClient)
        client_mock2 = MagicMock(spec=httpx.AsyncClient)
        client_mock3 = MagicMock(spec=httpx.AsyncClient)

        # Use side_effect to return a different mock each time
        with patch(
            "httpx.AsyncClient", side_effect=[client_mock1, client_mock2, client_mock3]
        ):
            await pool.initialize("https://test.api", {"Authorization": "Bearer test"})

            # Verify we have 3 connections created
            assert len(pool.connections) == 3

            # All connections should be in the available set
            assert len(pool.available_connections) == 3

            # Verify each client is in both collections
            for client in [client_mock1, client_mock2, client_mock3]:
                assert client in pool.connections
                assert client in pool.available_connections

    @pytest.mark.asyncio
    async def test_acquire_and_release(self):
        """Test acquire and release connections."""
        pool = ConnectionPool("test_provider", 2)

        # Create some mock clients
        client1 = MagicMock(spec=httpx.AsyncClient)
        client2 = MagicMock(spec=httpx.AsyncClient)

        # Add them to the pool
        pool.connections = [client1, client2]
        pool.available_connections = {client1, client2}

        # Use the acquire context manager
        async with pool.acquire() as client:
            assert client in [client1, client2]
            assert len(pool.available_connections) == 1  # One client is in use

        # After the context manager exits, the client should be back in the pool
        assert len(pool.available_connections) == 2

    @pytest.mark.asyncio
    async def test_acquire_no_available_connections(self):
        """Test acquire creates a new connection if none are available."""
        pool = ConnectionPool("test_provider", 2)

        # Create a mock client but don't add it to available_connections
        client1 = MagicMock(spec=httpx.AsyncClient)
        pool.connections = [client1]
        pool.available_connections = set()

        # Mock httpx.AsyncClient to return a specific mock for the new connection
        client2 = MagicMock(spec=httpx.AsyncClient)
        with patch("httpx.AsyncClient", return_value=client2):
            async with pool.acquire() as client:
                assert client == client2
                assert len(pool.connections) == 2
                assert len(pool.available_connections) == 0

            # After the context manager exits, the client should be back in the pool
            assert len(pool.available_connections) == 1
            assert client2 in pool.available_connections

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method closes all connections."""
        pool = ConnectionPool("test_provider", 2)

        # Create mock clients with aclose method
        client1 = MagicMock(spec=httpx.AsyncClient)
        client1.aclose = AsyncMock()
        client2 = MagicMock(spec=httpx.AsyncClient)
        client2.aclose = AsyncMock()

        # Add them to the pool
        pool.connections = [client1, client2]
        pool.available_connections = {client1, client2}

        # Close the pool
        await pool.close()

        # Verify both clients were closed
        client1.aclose.assert_called_once()
        client2.aclose.assert_called_once()

        # Verify the pool is empty
        assert len(pool.connections) == 0
        assert len(pool.available_connections) == 0


class TestConnectionManagement:
    """Tests for connection management functions."""

    @pytest.mark.asyncio
    async def test_get_connection_pool(self, reset_connection_pools):
        """Test get_connection_pool function."""
        # Add a mock pool to the global dictionary
        mock_pool = MagicMock(spec=ConnectionPool)
        _connection_pools["test_provider"] = mock_pool

        # Get the pool
        pool = get_connection_pool("test_provider")
        assert pool == mock_pool

        # Try to get a non-existent pool
        pool = get_connection_pool("non_existent")
        assert pool is None

    @pytest.mark.asyncio
    async def test_get_connection(self, reset_connection_pools):
        """Test get_connection context manager."""
        # Create a mock pool with proper async context manager behavior
        mock_pool = MagicMock(spec=ConnectionPool)
        mock_client = MagicMock(spec=httpx.AsyncClient)

        # Setup an async context manager for pool.acquire
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_client
        mock_pool.acquire.return_value = cm

        # Add the pool to the global dictionary
        _connection_pools["test_provider"] = mock_pool

        # Use the context manager
        async with get_connection("test_provider") as client:
            assert client == mock_client

        # Try with a non-existent provider
        with pytest.raises(ValueError, match="Provider non_existent not registered"):
            async with get_connection("non_existent"):
                pass

    @pytest.mark.asyncio
    async def test_setup_connection_pools(self, reset_connection_pools):
        """Test setup_connection_pools function."""
        # Mock the providers
        mock_provider1 = MagicMock()
        mock_provider1.name = "provider1"
        mock_provider1.base_url = "https://api1.test"
        mock_provider1.api_key = "key1"

        mock_provider2 = MagicMock()
        mock_provider2.name = "provider2"
        mock_provider2.base_url = "https://api2.test"
        mock_provider2.api_key = "key2"

        providers = {"provider1": mock_provider1, "provider2": mock_provider2}

        # Mock the get_llm_providers function and initialize_providers
        with (
            patch("src.llm.connection_pool.get_llm_providers", return_value=providers),
            patch(
                "src.llm.connection_pool.initialize_providers", new_callable=AsyncMock
            ),
        ):
            # Mock the ConnectionPool.initialize method
            with patch.object(
                ConnectionPool, "initialize", new_callable=AsyncMock
            ) as mock_initialize:
                await setup_connection_pools()

                # Verify pools were created
                assert len(_connection_pools) == 2
                assert "provider1" in _connection_pools
                assert "provider2" in _connection_pools

                # Verify initialize was called for each pool
                assert mock_initialize.call_count == 2

    @pytest.mark.asyncio
    async def test_close_connection_pools(self, reset_connection_pools):
        """Test close_connection_pools function."""
        # Create mock pools
        mock_pool1 = MagicMock(spec=ConnectionPool)
        mock_pool1.close = AsyncMock()

        mock_pool2 = MagicMock(spec=ConnectionPool)
        mock_pool2.close = AsyncMock()

        # Add the pools to the global dictionary
        _connection_pools["provider1"] = mock_pool1
        _connection_pools["provider2"] = mock_pool2

        # Close the pools
        await close_connection_pools()

        # Verify both pools were closed
        mock_pool1.close.assert_called_once()
        mock_pool2.close.assert_called_once()

        # Verify the global dictionary is empty
        assert len(_connection_pools) == 0


@pytest.mark.asyncio
async def test_connection_pool_integration():
    """Integration test for ConnectionPool."""
    # This test demonstrates how ConnectionPool would be used in practice

    # Create a pool with mock clients
    pool = ConnectionPool("test_provider", 2)

    # Create mock clients directly instead of trying to spec another mock
    mock_client1 = MagicMock()
    mock_client1.aclose = AsyncMock()

    mock_client2 = MagicMock()
    mock_client2.aclose = AsyncMock()

    # Mock httpx.AsyncClient to return our pre-created mocks
    with patch("httpx.AsyncClient", side_effect=[mock_client1, mock_client2]):
        # Initialize the pool
        await pool.initialize("https://test.api", {"Authorization": "Bearer test"})

        # Check our mocks were added to the pool
        assert len(pool.connections) == 2
        assert mock_client1 in pool.connections
        assert mock_client2 in pool.connections

        # Acquire connections and use them
        async with pool.acquire() as client1:
            assert client1 in [mock_client1, mock_client2]

            # Acquire a second connection
            async with pool.acquire() as client2:
                assert client2 in [mock_client1, mock_client2]
                assert client1 != client2  # Should get different clients

        # Close the pool
        await pool.close()

        # Verify both clients were closed
        mock_client1.aclose.assert_called_once()
        mock_client2.aclose.assert_called_once()
