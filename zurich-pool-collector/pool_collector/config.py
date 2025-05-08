from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class WebSocketConfig:
    url: str
    retry_interval_seconds: int
    timeout_seconds: int
    ping_interval_seconds: float
    ping_timeout_seconds: float


@dataclass
class MetricsConfig:
    port: int
    endpoint: str
    namespace: str


@dataclass
class PoolConfig:
    uid: str
    name: str


@dataclass
class LoggingConfig:
    level: str
    format: str


@dataclass
class AppConfig:
    websocket: WebSocketConfig
    metrics: MetricsConfig
    pools: List[PoolConfig]
    logging: LoggingConfig


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path("config.yml")

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    return AppConfig(
        websocket=WebSocketConfig(**config_data["websocket"]),
        metrics=MetricsConfig(**config_data["metrics"]),
        pools=[PoolConfig(**pool) for pool in config_data["pools"]],
        logging=LoggingConfig(**config_data["logging"]),
    )
