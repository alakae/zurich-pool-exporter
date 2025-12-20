import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import CollectorRegistry
from websockets.exceptions import ConnectionClosed, WebSocketException

from pool_exporter.api_types import PoolOccupancyData
from pool_exporter.config import (
    AppConfig,
    LoggingConfig,
    MetricsConfig,
    OccupancyConfig,
    PoolConfig,
    TemperatureConfig,
)
from pool_exporter.metrics import PoolMetrics
from pool_exporter.occupancy_collector import OccupancyCollector


@pytest.fixture
def mock_config() -> AppConfig:
    """Create a mock configuration for testing."""
    return AppConfig(
        occupancy=OccupancyConfig(
            url="wss://test.com/occupancy",
            retry_interval_seconds=1,
            timeout_seconds=5,
            ping_interval_seconds=20.0,
            ping_timeout_seconds=10.0,
        ),
        temperature=TemperatureConfig(
            url="https://test.com", poll_interval_seconds=300, timeout_seconds=10
        ),
        metrics=MetricsConfig(port=8000, endpoint="/metrics", namespace="zurich_pools"),
        pools=[
            PoolConfig(uid="SSD-1", name="Pool One"),
            PoolConfig(uid="SSD-2", name="Pool Two"),
        ],
        logging=LoggingConfig(level="INFO", format="%(message)s"),
    )


@pytest.fixture
def custom_registry() -> CollectorRegistry:
    """Create a custom Prometheus registry for each test to avoid conflicts."""
    return CollectorRegistry()


@pytest.fixture
def mock_metrics(mock_config: AppConfig, custom_registry: CollectorRegistry) -> PoolMetrics:
    """Create a mock PoolMetrics instance with custom registry."""
    with patch("pool_exporter.metrics.start_http_server"):
        with patch("pool_exporter.metrics.Gauge") as mock_gauge:
            from prometheus_client import Gauge

            def create_gauge(name: str, doc: str, labelnames: list[str]) -> Gauge:
                return Gauge(name, doc, labelnames, registry=custom_registry)

            mock_gauge.side_effect = create_gauge
            return PoolMetrics(mock_config)


@pytest.fixture
def collector(mock_config: AppConfig, mock_metrics: PoolMetrics) -> OccupancyCollector:
    """Create an OccupancyCollector instance."""
    return OccupancyCollector(mock_config, mock_metrics)


@pytest.mark.asyncio
async def test_process_message_valid_data(
    collector: OccupancyCollector, mock_metrics: PoolMetrics
) -> None:
    """Test processing a valid WebSocket message."""
    message = json.dumps(
        [
            {
                "uid": "SSD-1",
                "name": "Pool One",
                "freespace": 50,
                "maxspace": 100,
                "currentfill": "50",
            }
        ]
    )

    with patch.object(mock_metrics, "update_occupancy_metrics") as mock_update:
        await collector.process_message(message)

    mock_update.assert_called_once()
    call_args = mock_update.call_args[0][0]
    assert isinstance(call_args, PoolOccupancyData)
    assert call_args.uid == "SSD-1"
    assert call_args.currentfill == 50


@pytest.mark.asyncio
async def test_process_message_multiple_pools(
    collector: OccupancyCollector, mock_metrics: PoolMetrics
) -> None:
    """Test processing a message with multiple pools."""
    message = json.dumps(
        [
            {
                "uid": "SSD-1",
                "name": "Pool One",
                "freespace": 50,
                "maxspace": 100,
                "currentfill": "50",
            },
            {
                "uid": "SSD-2",
                "name": "Pool Two",
                "freespace": 25,
                "maxspace": 75,
                "currentfill": "50",
            },
        ]
    )

    with patch.object(mock_metrics, "update_occupancy_metrics") as mock_update:
        await collector.process_message(message)

    assert mock_update.call_count == 2


@pytest.mark.asyncio
async def test_process_message_zero_capacity(
    collector: OccupancyCollector, mock_metrics: PoolMetrics
) -> None:
    """Test processing a message with zero capacity (edge case)."""
    message = json.dumps(
        [
            {
                "uid": "SSD-1",
                "name": "Pool One",
                "freespace": 0,
                "maxspace": 0,  # Edge case: zero capacity
                "currentfill": "0",
            }
        ]
    )

    with patch.object(mock_metrics, "update_occupancy_metrics") as mock_update:
        await collector.process_message(message)

    mock_update.assert_called_once()
    call_args = mock_update.call_args[0][0]
    assert call_args.maxspace == 0
    assert call_args.currentfill == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        "not valid json {[",  # Invalid JSON
        json.dumps({"uid": "SSD-1", "name": "Pool One"}),  # Wrong format (not a list)
        json.dumps([{"uid": "SSD-1", "name": "Pool One"}]),  # Missing required fields
    ],
)
async def test_process_message_invalid_data(
    collector: OccupancyCollector, message: str
) -> None:
    """Test processing messages with various invalid data formats."""
    # Should not raise an exception (errors are logged)
    await collector.process_message(message)


@pytest.mark.asyncio
async def test_connect_websocket_success(collector: OccupancyCollector) -> None:
    """Test successful WebSocket connection."""
    mock_websocket = AsyncMock()
    collector.running = True

    # Mock connect as an async function that returns the mock websocket
    async def mock_connect(*args: object, **kwargs: object) -> AsyncMock:
        collector.running = False  # Stop to prevent infinite loop
        return mock_websocket

    with patch("pool_exporter.occupancy_collector.websockets.connect", side_effect=mock_connect):
        result = await collector.connect_websocket()

    assert result == mock_websocket


@pytest.mark.asyncio
async def test_connect_websocket_failure_retry(collector: OccupancyCollector) -> None:
    """Test WebSocket connection failure with retry logic."""
    collector.running = True

    # Simulate connection failure, then stop
    async def side_effect(*args: object, **kwargs: object) -> None:
        collector.running = False  # Stop after first attempt
        raise WebSocketException("Connection failed")

    with patch(
        "pool_exporter.occupancy_collector.websockets.connect",
        side_effect=side_effect,
    ):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await collector.connect_websocket()

    assert result is None


@pytest.mark.asyncio
async def test_connect_websocket_not_running(collector: OccupancyCollector) -> None:
    """Test that connect_websocket returns None when not running."""
    collector.running = False

    result = await collector.connect_websocket()

    assert result is None


@pytest.mark.asyncio
async def test_run_success(collector: OccupancyCollector, mock_metrics: PoolMetrics) -> None:
    """Test successful run loop."""
    # Create a task that will run the collector and cancel it after a short delay
    async def run_with_timeout() -> None:
        # Stop the collector after receiving one message
        await asyncio.sleep(0.01)
        collector.stop()

    mock_websocket = AsyncMock()
    mock_websocket.send = AsyncMock()
    mock_websocket.close = AsyncMock()

    message_count = 0

    async def mock_iter(self: object) -> object:
        nonlocal message_count
        # Yield one message
        message_count += 1
        yield json.dumps(
            [
                {
                    "uid": "SSD-1",
                    "name": "Pool One",
                    "freespace": 50,
                    "maxspace": 100,
                    "currentfill": "50",
                }
            ]
        )
        # Then wait to allow the timeout task to stop the collector
        await asyncio.sleep(0.02)

    mock_websocket.__aiter__ = lambda self: mock_iter(self)

    async def mock_connect() -> AsyncMock:
        return mock_websocket

    with patch.object(collector, "connect_websocket", side_effect=mock_connect):
        with patch.object(mock_metrics, "update_occupancy_metrics"):
            # Run both tasks concurrently
            await asyncio.gather(collector.run(), run_with_timeout())

    assert message_count == 1
    mock_websocket.send.assert_called_once_with("all")
    assert not collector.running


@pytest.mark.asyncio
async def test_run_connection_closed(collector: OccupancyCollector) -> None:
    """Test run loop handling ConnectionClosed exception."""
    async def run_with_timeout() -> None:
        await asyncio.sleep(0.01)
        collector.stop()

    mock_websocket = AsyncMock()
    mock_websocket.send = AsyncMock()
    mock_websocket.close = AsyncMock()

    # Simulate ConnectionClosed exception
    async def mock_iter(self: object) -> None:
        raise ConnectionClosed(None, None)
        yield  # Make this a generator

    mock_websocket.__aiter__ = lambda self: mock_iter(self)

    async def mock_connect() -> AsyncMock:
        return mock_websocket

    with patch.object(collector, "connect_websocket", side_effect=mock_connect):
        await asyncio.gather(collector.run(), run_with_timeout())

    assert not collector.running


@pytest.mark.asyncio
async def test_run_websocket_exception(collector: OccupancyCollector) -> None:
    """Test run loop handling generic WebSocket exception."""
    async def run_with_timeout() -> None:
        await asyncio.sleep(0.01)
        collector.stop()

    mock_websocket = AsyncMock()
    mock_websocket.send = AsyncMock()
    mock_websocket.close = AsyncMock()

    # Simulate exception during message iteration
    async def mock_iter(self: object) -> None:
        raise Exception("Unexpected error")
        yield  # Make this a generator

    mock_websocket.__aiter__ = lambda self: mock_iter(self)

    async def mock_connect() -> AsyncMock:
        return mock_websocket

    with patch.object(collector, "connect_websocket", side_effect=mock_connect):
        await asyncio.gather(collector.run(), run_with_timeout())

    assert not collector.running


@pytest.mark.asyncio
async def test_run_no_connection(collector: OccupancyCollector) -> None:
    """Test run loop when connection fails."""
    # First attempt returns None, then stop
    call_count = 0

    async def mock_connect() -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return None
        collector.stop()
        return None

    with patch.object(collector, "connect_websocket", side_effect=mock_connect):
        await collector.run()

    assert not collector.running


def test_stop(collector: OccupancyCollector) -> None:
    """Test stop method."""
    collector.running = True
    collector.stop()
    assert not collector.running


@pytest.mark.asyncio
async def test_run_reconnect_after_connection_closed(
    collector: OccupancyCollector,
) -> None:
    """Test that run attempts to reconnect after connection is closed."""
    mock_websocket = AsyncMock()
    mock_websocket.send = AsyncMock()
    mock_websocket.close = AsyncMock()

    connection_attempts = 0

    async def mock_connect_impl() -> AsyncMock | None:
        nonlocal connection_attempts
        connection_attempts += 1
        if connection_attempts == 1:
            return mock_websocket
        else:
            collector.stop()
            return None

    async def mock_iter() -> None:
        raise ConnectionClosed(None, None)
        yield  # Make this a generator

    mock_websocket.__aiter__ = mock_iter

    with patch.object(collector, "connect_websocket", side_effect=mock_connect_impl):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await collector.run()

    # Should attempt to connect twice (initial + reconnect)
    assert connection_attempts == 2
    assert not collector.running
