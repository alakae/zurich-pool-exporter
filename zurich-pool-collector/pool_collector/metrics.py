import logging
from typing import Dict, Set

from prometheus_client import Gauge, start_http_server
from config import AppConfig, PoolConfig


logger = logging.getLogger(__name__)


class PoolMetrics:
    """Prometheus metrics for pool occupancy data."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.namespace = config.metrics.namespace
        self.pool_uids: Set[str] = {pool.uid for pool in config.pools}

        # Create Prometheus metrics
        self.current_fill = Gauge(
            f"{self.namespace}_current_fill",
            "Current number of visitors at the pool",
            ["pool_uid", "pool_name"],
        )

        self.free_space = Gauge(
            f"{self.namespace}_free_space",
            "Available capacity remaining at the pool",
            ["pool_uid", "pool_name"],
        )

        self.max_space = Gauge(
            f"{self.namespace}_max_space",
            "Maximum capacity of the pool",
            ["pool_uid", "pool_name"],
        )

        self.occupancy_percentage = Gauge(
            f"{self.namespace}_occupancy_percentage",
            "Percentage of pool capacity currently in use",
            ["pool_uid", "pool_name"],
        )

    def start_metrics_server(self) -> None:
        """Start Prometheus metrics HTTP server."""
        start_http_server(self.config.metrics.port)
        logger.info(
            f"Metrics server started at http://localhost:{self.config.metrics.port}{self.config.metrics.endpoint}"
        )

    def update_pool_metrics(self, pool_data: Dict) -> None:
        """Update metrics for a single pool."""
        pool_uid = pool_data.get("uid")
        if not pool_uid or pool_uid not in self.pool_uids:
            return

        pool_name = pool_data.get("name", "Unknown")

        # Get metrics values with fallbacks to 0
        current_fill = int(pool_data.get("currentfill", 0))
        free_space = int(pool_data.get("freespace", 0))
        max_space = int(pool_data.get("maxspace", 0))

        # Calculate occupancy percentage, handling potential division by zero
        occupancy_percentage: float = 0
        if max_space > 0:
            occupancy_percentage = (current_fill / max_space) * 100

        # Update Prometheus metrics
        self.current_fill.labels(pool_uid=pool_uid, pool_name=pool_name).set(
            current_fill
        )
        self.free_space.labels(pool_uid=pool_uid, pool_name=pool_name).set(free_space)
        self.max_space.labels(pool_uid=pool_uid, pool_name=pool_name).set(max_space)
        self.occupancy_percentage.labels(pool_uid=pool_uid, pool_name=pool_name).set(
            occupancy_percentage
        )

        logger.debug(
            f"Updated metrics for pool {pool_name} (ID: {pool_uid}): "
            f"current: {current_fill}, free: {free_space}, max: {max_space}, "
            f"occupancy: {occupancy_percentage:.1f}%"
        )
