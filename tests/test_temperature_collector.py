import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest
from prometheus_client import CollectorRegistry

from pool_exporter.api_types import TemperatureData
from pool_exporter.config import (
    AppConfig,
    LoggingConfig,
    MetricsConfig,
    OccupancyConfig,
    PoolConfig,
    TemperatureConfig,
)
from pool_exporter.metrics import PoolMetrics
from pool_exporter.temperature_collector import TemperatureCollector


@pytest.fixture
def mock_config() -> AppConfig:
    """Create a mock configuration for testing."""
    return AppConfig(
        occupancy=OccupancyConfig(
            url="wss://test.com",
            retry_interval_seconds=10,
            timeout_seconds=5,
            ping_interval_seconds=20.0,
            ping_timeout_seconds=10.0,
        ),
        temperature=TemperatureConfig(
            url="https://test.com/temperature.xml",
            poll_interval_seconds=1,  # Short interval for testing
            timeout_seconds=10,
        ),
        metrics=MetricsConfig(port=8000, endpoint="/metrics", namespace="zurich_pools"),
        pools=[
            PoolConfig(uid="SSD-1", name="Pool One", alt_uid="alt-1"),
            PoolConfig(uid="SSD-2", name="Pool Two"),
            PoolConfig(uid="SSD-3", name="Pool Three", hardcoded_temperatur=25),
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
def collector(mock_config: AppConfig, mock_metrics: PoolMetrics) -> TemperatureCollector:
    """Create a TemperatureCollector instance."""
    return TemperatureCollector(mock_config, mock_metrics)


@pytest.mark.asyncio
async def test_fetch_temperature_data_success(collector: TemperatureCollector) -> None:
    """Test successful temperature data fetching."""
    with patch.object(collector, "fetch_temperature_data", return_value="<xml>test data</xml>"):
        result = await collector.fetch_temperature_data()

    assert result == "<xml>test data</xml>"


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [404, 500, 503])
async def test_fetch_temperature_data_http_errors(
    collector: TemperatureCollector, status_code: int
) -> None:
    """Test fetching temperature data with various HTTP error codes."""
    mock_response = AsyncMock()
    mock_response.status = status_code

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock()

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await collector.fetch_temperature_data()

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception",
    [
        aiohttp.ClientError("Timeout"),
        Exception("Unexpected error"),
    ],
)
async def test_fetch_temperature_data_exceptions(
    collector: TemperatureCollector, exception: Exception
) -> None:
    """Test fetching temperature data with various exceptions."""
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(side_effect=exception)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await collector.fetch_temperature_data()

    assert result is None


def test_parse_temperature_data_valid(collector: TemperatureCollector) -> None:
    """Test parsing valid XML temperature data."""
    xml_data = """<?xml version="1.0"?>
<baths>
    <bath>
        <poiid>SSD-1</poiid>
        <title>Pool One</title>
        <temperatureWater>25.5</temperatureWater>
        <openClosedTextPlain>Open</openClosedTextPlain>
        <dateModified>2025-01-01T12:00:00</dateModified>
    </bath>
</baths>
"""

    result = collector.parse_temperature_data(xml_data)

    assert len(result) == 1
    assert result[0].pool_id == "ssd-1"  # Converted to lowercase
    assert result[0].title == "Pool One"
    assert result[0].temperature == 25.5
    assert result[0].status == "Open"
    assert result[0].last_updated == "2025-01-01T12:00:00"


def test_parse_temperature_data_multiple_pools(collector: TemperatureCollector) -> None:
    """Test parsing XML with multiple pools."""
    xml_data = """<?xml version="1.0"?>
<baths>
    <bath>
        <poiid>SSD-1</poiid>
        <title>Pool One</title>
        <temperatureWater>25.5</temperatureWater>
    </bath>
    <bath>
        <poiid>SSD-2</poiid>
        <title>Pool Two</title>
        <temperatureWater>26.0</temperatureWater>
    </bath>
</baths>
"""

    result = collector.parse_temperature_data(xml_data)

    assert len(result) == 2
    assert result[0].pool_id == "ssd-1"
    assert result[1].pool_id == "ssd-2"


def test_parse_temperature_data_zero_temperature(collector: TemperatureCollector) -> None:
    """Test parsing temperature data with 0°C temperature (edge case)."""
    xml_data = """<?xml version="1.0"?>
<baths>
    <bath>
        <poiid>SSD-1</poiid>
        <title>Frozen Pool</title>
        <temperatureWater>0.0</temperatureWater>
    </bath>
</baths>
"""

    result = collector.parse_temperature_data(xml_data)

    assert len(result) == 1
    assert result[0].temperature == 0.0


def test_parse_temperature_data_missing_temperature(
    collector: TemperatureCollector,
) -> None:
    """Test parsing XML with missing temperature field (edge case)."""
    xml_data = """<?xml version="1.0"?>
<baths>
    <bath>
        <poiid>SSD-1</poiid>
        <title>Pool One</title>
        <!-- Missing temperatureWater -->
    </bath>
</baths>
"""

    result = collector.parse_temperature_data(xml_data)

    # Should return empty list because temperature is required
    assert len(result) == 0


def test_parse_temperature_data_missing_optional_fields(
    collector: TemperatureCollector,
) -> None:
    """Test parsing XML with missing optional fields."""
    xml_data = """<?xml version="1.0"?>
<baths>
    <bath>
        <poiid>SSD-1</poiid>
        <title>Pool One</title>
        <temperatureWater>25.5</temperatureWater>
        <!-- Missing openClosedTextPlain and dateModified -->
    </bath>
</baths>
"""

    result = collector.parse_temperature_data(xml_data)

    assert len(result) == 1
    assert result[0].status == "Unknown"  # Default value
    assert result[0].last_updated is None


def test_parse_temperature_data_invalid_temperature(
    collector: TemperatureCollector,
) -> None:
    """Test parsing XML with invalid temperature value."""
    xml_data = """<?xml version="1.0"?>
<baths>
    <bath>
        <poiid>SSD-1</poiid>
        <title>Pool One</title>
        <temperatureWater>not_a_number</temperatureWater>
    </bath>
</baths>
"""

    result = collector.parse_temperature_data(xml_data)

    # Should skip pools with invalid temperature
    assert len(result) == 0


def test_parse_temperature_data_malformed_xml(collector: TemperatureCollector) -> None:
    """Test parsing malformed XML (edge case)."""
    xml_data = "<baths><bath><poiid>SSD-1</poiid>"  # Malformed XML

    result = collector.parse_temperature_data(xml_data)

    # Should return empty list on parse error
    assert len(result) == 0


def test_parse_temperature_data_empty_xml(collector: TemperatureCollector) -> None:
    """Test parsing empty XML."""
    xml_data = """<?xml version="1.0"?>
<baths>
</baths>
"""

    result = collector.parse_temperature_data(xml_data)

    assert len(result) == 0


def test_update_metrics(collector: TemperatureCollector, mock_metrics: PoolMetrics) -> None:
    """Test updating metrics with temperature data."""
    pool_data = [
        TemperatureData(
            pool_id="SSD-1",
            temperature=25.5,
            title="Pool One",
        )
    ]

    with patch.object(mock_metrics, "update_temperature_metrics") as mock_update:
        collector.update_metrics(pool_data)

    mock_update.assert_called_once()
    assert mock_update.call_args[0][0] == pool_data[0]


@pytest.mark.asyncio
async def test_collect_success(
    collector: TemperatureCollector, mock_metrics: PoolMetrics
) -> None:
    """Test successful temperature collection."""
    xml_data = """<?xml version="1.0"?>
<baths>
    <bath>
        <poiid>SSD-1</poiid>
        <title>Pool One</title>
        <temperatureWater>25.5</temperatureWater>
    </bath>
</baths>
"""

    with patch.object(
        collector, "fetch_temperature_data", return_value=xml_data
    ) as mock_fetch:
        with patch.object(mock_metrics, "update_temperature_metrics") as mock_update:
            await collector.collect()

    mock_fetch.assert_called_once()
    mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_collect_fetch_failure(collector: TemperatureCollector) -> None:
    """Test collect when fetch fails."""
    with patch.object(collector, "fetch_temperature_data", return_value=None) as mock_fetch:
        await collector.collect()

    mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_collect_parse_failure(
    collector: TemperatureCollector, mock_metrics: PoolMetrics
) -> None:
    """Test collect when parsing returns no data."""
    with patch.object(collector, "fetch_temperature_data", return_value="<invalid></invalid>"):
        with patch.object(mock_metrics, "update_temperature_metrics") as mock_update:
            await collector.collect()

    # update_metrics should not be called if parsing fails
    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_run(collector: TemperatureCollector) -> None:
    """Test the run loop."""
    collect_count = 0

    async def mock_collect() -> None:
        nonlocal collect_count
        collect_count += 1
        if collect_count >= 2:
            collector.stop()

    with patch.object(collector, "collect", side_effect=mock_collect):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await collector.run()

    assert collect_count == 2
    assert not collector.running


@pytest.mark.asyncio
async def test_run_with_exception(collector: TemperatureCollector) -> None:
    """Test run loop handling exceptions during collection."""
    collect_count = 0

    async def mock_collect() -> None:
        nonlocal collect_count
        collect_count += 1
        if collect_count == 1:
            raise Exception("Collection error")
        else:
            collector.stop()

    with patch.object(collector, "collect", side_effect=mock_collect):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await collector.run()

    # Should continue after exception
    assert collect_count == 2
    assert not collector.running


def test_stop(collector: TemperatureCollector) -> None:
    """Test stop method."""
    collector.running = True
    collector.stop()
    assert not collector.running


def test_publish_hardcoded_temperature(
    mock_config: AppConfig, custom_registry: CollectorRegistry
) -> None:
    """Test that hardcoded temperatures are published on initialization."""
    with patch("pool_exporter.metrics.start_http_server"):
        with patch("pool_exporter.metrics.Gauge") as mock_gauge:
            from prometheus_client import Gauge

            def create_gauge(name: str, doc: str, labelnames: list[str]) -> Gauge:
                return Gauge(name, doc, labelnames, registry=custom_registry)

            mock_gauge.side_effect = create_gauge
            mock_metrics = PoolMetrics(mock_config)

    with patch.object(mock_metrics, "update_temperature_metrics") as mock_update:
        collector = TemperatureCollector(mock_config, mock_metrics)

    # Should be called once for the pool with hardcoded temperature (SSD-3)
    mock_update.assert_called_once()
    call_args = mock_update.call_args[0][0]
    assert call_args.pool_id == "SSD-3"
    assert call_args.temperature == 25


def test_parse_temperature_data_empty_string_fields(
    collector: TemperatureCollector,
) -> None:
    """Test parsing XML with empty string fields."""
    xml_data = """<?xml version="1.0"?>
<baths>
    <bath>
        <poiid></poiid>
        <title>  </title>
        <temperatureWater>25.5</temperatureWater>
    </bath>
</baths>
"""

    result = collector.parse_temperature_data(xml_data)

    # Should handle empty/whitespace strings
    # When poiid.text is empty string, calling .lower() if empty_string returns None
    assert len(result) == 1
    assert result[0].pool_id is None
    assert result[0].temperature == 25.5


def test_parse_temperature_data_case_insensitive_pool_id(
    collector: TemperatureCollector,
) -> None:
    """Test that pool IDs are converted to lowercase."""
    xml_data = """<?xml version="1.0"?>
<baths>
    <bath>
        <poiid>SSD-1</poiid>
        <title>Pool One</title>
        <temperatureWater>25.5</temperatureWater>
    </bath>
</baths>
"""

    result = collector.parse_temperature_data(xml_data)

    assert len(result) == 1
    assert result[0].pool_id == "ssd-1"  # Lowercase
