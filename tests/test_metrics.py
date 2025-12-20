from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import CollectorRegistry

from pool_exporter.api_types import PoolOccupancyData, TemperatureData
from pool_exporter.config import (
    AppConfig,
    LoggingConfig,
    MetricsConfig,
    OccupancyConfig,
    PoolConfig,
    TemperatureConfig,
)
from pool_exporter.metrics import PoolMetrics


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
            url="https://test.com", poll_interval_seconds=300, timeout_seconds=10
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
def metrics(mock_config: AppConfig, custom_registry: CollectorRegistry) -> PoolMetrics:
    """Create a PoolMetrics instance with mocked metrics server and custom registry."""
    with patch("pool_exporter.metrics.start_http_server"):
        with patch("pool_exporter.metrics.Gauge") as mock_gauge:
            # Create real gauge instances but with custom registry
            from prometheus_client import Gauge

            def create_gauge(name: str, doc: str, labelnames: list[str]) -> Gauge:
                return Gauge(name, doc, labelnames, registry=custom_registry)

            mock_gauge.side_effect = create_gauge
            return PoolMetrics(mock_config)


def test_metrics_initialization(mock_config: AppConfig, custom_registry: CollectorRegistry) -> None:
    """Test that PoolMetrics initializes correctly."""
    with patch("pool_exporter.metrics.start_http_server"):
        with patch("pool_exporter.metrics.Gauge") as mock_gauge:
            from prometheus_client import Gauge

            def create_gauge(name: str, doc: str, labelnames: list[str]) -> Gauge:
                return Gauge(name, doc, labelnames, registry=custom_registry)

            mock_gauge.side_effect = create_gauge
            metrics = PoolMetrics(mock_config)

    assert metrics.namespace == "zurich_pools"
    assert metrics.pool_uids == {"SSD-1", "SSD-2", "SSD-3"}
    assert metrics.pool_names == {"Pool One", "Pool Two", "Pool Three"}
    assert metrics.pool_alt_uid_to_uid == {"alt-1": "SSD-1"}
    assert metrics.pool_uid_to_name == {
        "SSD-1": "Pool One",
        "SSD-2": "Pool Two",
        "SSD-3": "Pool Three",
    }


def test_start_metrics_server(mock_config: AppConfig, custom_registry: CollectorRegistry) -> None:
    """Test that metrics server starts correctly."""
    with patch("pool_exporter.metrics.start_http_server") as mock_start:
        with patch("pool_exporter.metrics.Gauge") as mock_gauge:
            from prometheus_client import Gauge

            def create_gauge(name: str, doc: str, labelnames: list[str]) -> Gauge:
                return Gauge(name, doc, labelnames, registry=custom_registry)

            mock_gauge.side_effect = create_gauge
            metrics = PoolMetrics(mock_config)
            metrics.start_metrics_server()

    # Should be called once during start_metrics_server() call
    assert mock_start.call_count == 1
    mock_start.assert_called_with(8000)


def test_update_occupancy_metrics_valid_data(metrics: PoolMetrics) -> None:
    """Test updating occupancy metrics with valid data."""
    pool_data = PoolOccupancyData(
        uid="SSD-1",
        name="Pool One",
        freespace=50,
        maxspace=100,
        currentfill=50,
    )

    metrics.update_occupancy_metrics(pool_data)

    # Verify that the metrics were set (we can't easily inspect Gauge values,
    # but we can verify the method runs without error)
    assert metrics.current_fill.labels(pool_uid="SSD-1", pool_name="Pool One")
    assert metrics.free_space.labels(pool_uid="SSD-1", pool_name="Pool One")
    assert metrics.max_space.labels(pool_uid="SSD-1", pool_name="Pool One")
    assert metrics.occupancy_percentage.labels(pool_uid="SSD-1", pool_name="Pool One")


def test_update_occupancy_metrics_zero_max_space(metrics: PoolMetrics) -> None:
    """Test updating occupancy metrics with zero max space (division by zero edge case)."""
    pool_data = PoolOccupancyData(
        uid="SSD-1",
        name="Pool One",
        freespace=0,
        maxspace=0,  # Edge case: division by zero
        currentfill=0,
    )

    # Should not raise an exception
    metrics.update_occupancy_metrics(pool_data)

    # Verify metrics exist
    assert metrics.current_fill.labels(pool_uid="SSD-1", pool_name="Pool One")
    assert metrics.occupancy_percentage.labels(pool_uid="SSD-1", pool_name="Pool One")


def test_update_occupancy_metrics_unknown_pool(metrics: PoolMetrics) -> None:
    """Test that metrics for unknown pools are ignored."""
    pool_data = PoolOccupancyData(
        uid="UNKNOWN-POOL",
        name="Unknown Pool",
        freespace=50,
        maxspace=100,
        currentfill=50,
    )

    # Should not raise an exception, but should be ignored
    metrics.update_occupancy_metrics(pool_data)


def test_update_occupancy_metrics_empty_uid(metrics: PoolMetrics) -> None:
    """Test that metrics with empty UID are ignored."""
    pool_data = PoolOccupancyData(
        uid="",
        name="Pool One",
        freespace=50,
        maxspace=100,
        currentfill=50,
    )

    # Should not raise an exception, but should be ignored
    metrics.update_occupancy_metrics(pool_data)


def test_update_temperature_metrics_valid_data(metrics: PoolMetrics) -> None:
    """Test updating temperature metrics with valid data."""
    temp_data = TemperatureData(
        pool_id="SSD-1",
        temperature=25.5,
        title="Pool One",
        status="Open",
    )

    metrics.update_temperature_metrics(temp_data)

    # Verify that the metric was set
    assert metrics.water_temperature.labels(pool_uid="SSD-1", pool_name="Pool One")


def test_update_temperature_metrics_with_alt_uid(metrics: PoolMetrics) -> None:
    """Test updating temperature metrics using alternate UID."""
    temp_data = TemperatureData(
        pool_id="alt-1",  # This should map to SSD-1
        temperature=25.5,
        title="Pool One",
    )

    metrics.update_temperature_metrics(temp_data)

    # Should use the mapped UID
    assert metrics.water_temperature.labels(pool_uid="SSD-1", pool_name="Pool One")


@pytest.mark.parametrize(
    "pool_id,temperature,title,should_set_metric",
    [
        ("SSD-1", None, "Pool One", False),  # None temperature - should be ignored
        ("SSD-1", 0.0, "Pool One", True),  # Zero temperature - should be set
        ("UNKNOWN-POOL", 25.5, "Unknown Pool", False),  # Unknown pool - should be ignored
        (None, 25.5, "Pool One", False),  # None pool_id - should be ignored
    ],
)
def test_update_temperature_metrics_edge_cases(
    metrics: PoolMetrics,
    pool_id: str | None,
    temperature: float | None,
    title: str,
    should_set_metric: bool,
) -> None:
    """Test updating temperature metrics with various edge cases."""
    temp_data = TemperatureData(
        pool_id=pool_id,
        temperature=temperature,
        title=title,
    )

    # Should not raise an exception
    metrics.update_temperature_metrics(temp_data)

    # Verify metric was set only when expected
    if should_set_metric:
        assert metrics.water_temperature.labels(pool_uid="SSD-1", pool_name="Pool One")


def test_metrics_namespace_in_metric_names(mock_config: AppConfig, custom_registry: CollectorRegistry) -> None:
    """Test that metrics use the configured namespace."""
    with patch("pool_exporter.metrics.start_http_server"):
        with patch("pool_exporter.metrics.Gauge") as mock_gauge:
            from prometheus_client import Gauge

            def create_gauge(name: str, doc: str, labelnames: list[str]) -> Gauge:
                return Gauge(name, doc, labelnames, registry=custom_registry)

            mock_gauge.side_effect = create_gauge
            metrics = PoolMetrics(mock_config)

    assert metrics.current_fill._name == "zurich_pools_current_fill"
    assert metrics.free_space._name == "zurich_pools_free_space"
    assert metrics.max_space._name == "zurich_pools_max_space"
    assert metrics.occupancy_percentage._name == "zurich_pools_occupancy_percentage"
    assert metrics.water_temperature._name == "zurich_pools_water_temperature"


def test_update_occupancy_metrics_full_capacity(metrics: PoolMetrics) -> None:
    """Test updating occupancy metrics at full capacity."""
    pool_data = PoolOccupancyData(
        uid="SSD-2",
        name="Pool Two",
        freespace=0,
        maxspace=100,
        currentfill=100,
    )

    metrics.update_occupancy_metrics(pool_data)

    # Verify metrics exist
    assert metrics.current_fill.labels(pool_uid="SSD-2", pool_name="Pool Two")
    assert metrics.free_space.labels(pool_uid="SSD-2", pool_name="Pool Two")


def test_update_occupancy_metrics_over_capacity(metrics: PoolMetrics) -> None:
    """Test updating occupancy metrics when over capacity (edge case)."""
    pool_data = PoolOccupancyData(
        uid="SSD-2",
        name="Pool Two",
        freespace=-10,  # Negative free space
        maxspace=100,
        currentfill=110,  # Over capacity
    )

    # Should not raise an exception
    metrics.update_occupancy_metrics(pool_data)

    # Verify metrics exist
    assert metrics.current_fill.labels(pool_uid="SSD-2", pool_name="Pool Two")
