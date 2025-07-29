from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class OccupancyConfig:
    url: str
    retry_interval_seconds: int
    timeout_seconds: int
    ping_interval_seconds: float
    ping_timeout_seconds: float


@dataclass
class TemperatureConfig:
    url: str
    poll_interval_seconds: int
    timeout_seconds: int


@dataclass
class MetricsConfig:
    port: int
    endpoint: str
    namespace: str


@dataclass
class PoolConfig:
    uid: str
    name: str
    alt_uid: str | None = None
    hardcoded_temperatur: int | None = None


@dataclass
class LoggingConfig:
    level: str
    format: str


@dataclass
class AppConfig:
    occupancy: OccupancyConfig
    temperature: TemperatureConfig
    metrics: MetricsConfig
    pools: list[PoolConfig]
    logging: LoggingConfig


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path("config.yml")

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    return AppConfig(
        occupancy=OccupancyConfig(**config_data["occupancy"]),
        temperature=TemperatureConfig(**config_data["temperature"]),
        metrics=MetricsConfig(**config_data["metrics"]),
        pools=[PoolConfig(**pool) for pool in config_data["pools"]],
        logging=LoggingConfig(**config_data["logging"]),
    )
