from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from pool_exporter.config import (
    AppConfig,
    LoggingConfig,
    MetricsConfig,
    OccupancyConfig,
    PoolConfig,
    TemperatureConfig,
    load_config,
)


def test_load_config_success() -> None:
    """Test successful configuration loading from YAML file."""
    config_yaml = """
occupancy:
  url: "wss://example.com/occupancy"
  retry_interval_seconds: 30
  timeout_seconds: 10
  ping_interval_seconds: 20.0
  ping_timeout_seconds: 10.0

temperature:
  url: "https://example.com/temperature.xml"
  poll_interval_seconds: 300
  timeout_seconds: 10

metrics:
  port: 8000
  endpoint: "/metrics"
  namespace: "zurich_pools"

pools:
  - uid: "SSD-1"
    name: "Pool One"
    alt_uid: "alt-1"
    hardcoded_temperatur: 25
  - uid: "SSD-2"
    name: "Pool Two"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""

    with patch("builtins.open", mock_open(read_data=config_yaml)):
        with patch("pathlib.Path.exists", return_value=True):
            config = load_config(Path("config.yml"))

    assert config.occupancy.url == "wss://example.com/occupancy"
    assert config.occupancy.retry_interval_seconds == 30
    assert config.occupancy.timeout_seconds == 10
    assert config.occupancy.ping_interval_seconds == 20.0
    assert config.occupancy.ping_timeout_seconds == 10.0

    assert config.temperature.url == "https://example.com/temperature.xml"
    assert config.temperature.poll_interval_seconds == 300
    assert config.temperature.timeout_seconds == 10

    assert config.metrics.port == 8000
    assert config.metrics.endpoint == "/metrics"
    assert config.metrics.namespace == "zurich_pools"

    assert len(config.pools) == 2
    assert config.pools[0].uid == "SSD-1"
    assert config.pools[0].name == "Pool One"
    assert config.pools[0].alt_uid == "alt-1"
    assert config.pools[0].hardcoded_temperatur == 25
    assert config.pools[1].uid == "SSD-2"
    assert config.pools[1].name == "Pool Two"
    assert config.pools[1].alt_uid is None
    assert config.pools[1].hardcoded_temperatur is None

    assert config.logging.level == "INFO"
    assert config.logging.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def test_load_config_file_not_found() -> None:
    """Test that FileNotFoundError is raised when config file doesn't exist."""
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config(Path("nonexistent.yml"))


def test_load_config_invalid_yaml() -> None:
    """Test that yaml.YAMLError is raised for malformed YAML."""
    invalid_yaml = """
occupancy:
  url: "wss://example.com
  # Missing closing quote
"""

    with patch("builtins.open", mock_open(read_data=invalid_yaml)):
        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(yaml.YAMLError):
                load_config(Path("config.yml"))


def test_load_config_missing_required_field() -> None:
    """Test that TypeError is raised when required fields are missing."""
    incomplete_yaml = """
occupancy:
  url: "wss://example.com/occupancy"
  # Missing retry_interval_seconds and other required fields
"""

    with patch("builtins.open", mock_open(read_data=incomplete_yaml)):
        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(TypeError):
                load_config(Path("config.yml"))


def test_load_config_default_path() -> None:
    """Test that load_config uses 'config.yml' as default path."""
    config_yaml = """
occupancy:
  url: "wss://example.com/occupancy"
  retry_interval_seconds: 30
  timeout_seconds: 10
  ping_interval_seconds: 20.0
  ping_timeout_seconds: 10.0

temperature:
  url: "https://example.com/temperature.xml"
  poll_interval_seconds: 300
  timeout_seconds: 10

metrics:
  port: 8000
  endpoint: "/metrics"
  namespace: "zurich_pools"

pools: []

logging:
  level: "INFO"
  format: "%(message)s"
"""

    with patch("builtins.open", mock_open(read_data=config_yaml)):
        with patch("pathlib.Path.exists", return_value=True):
            config = load_config()

    assert isinstance(config, AppConfig)
    assert config.occupancy.url == "wss://example.com/occupancy"


def test_config_dataclasses_immutable() -> None:
    """Test that config dataclasses can be instantiated."""
    occupancy = OccupancyConfig(
        url="wss://test.com",
        retry_interval_seconds=10,
        timeout_seconds=5,
        ping_interval_seconds=20.0,
        ping_timeout_seconds=10.0,
    )
    assert occupancy.url == "wss://test.com"

    temperature = TemperatureConfig(
        url="https://test.com", poll_interval_seconds=300, timeout_seconds=10
    )
    assert temperature.url == "https://test.com"

    metrics = MetricsConfig(port=8000, endpoint="/metrics", namespace="test")
    assert metrics.port == 8000

    pool = PoolConfig(uid="SSD-1", name="Test Pool", alt_uid="alt-1", hardcoded_temperatur=25)
    assert pool.uid == "SSD-1"
    assert pool.alt_uid == "alt-1"
    assert pool.hardcoded_temperatur == 25

    logging_config = LoggingConfig(level="DEBUG", format="%(message)s")
    assert logging_config.level == "DEBUG"

    app_config = AppConfig(
        occupancy=occupancy,
        temperature=temperature,
        metrics=metrics,
        pools=[pool],
        logging=logging_config,
    )
    assert isinstance(app_config, AppConfig)
