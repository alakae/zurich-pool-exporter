from typing import Protocol

from pool_exporter.config import AppConfig
from pool_exporter.metrics import PoolMetrics


class DataCollector(Protocol):
    """Protocol defining the interface for pool data collectors."""

    config: AppConfig
    metrics: PoolMetrics
    running: bool

    def __init__(self, config: AppConfig, metrics: PoolMetrics) -> None:
        """Initialize the collector with configuration and metrics."""
        ...

    async def run(self) -> None:
        """Run the data collector loop.

        This method should:
        - Set running=True
        - Start the main collection loop
        - Handle errors gracefully
        - Continue until running=False
        - Log start/stop events
        """
        ...

    def stop(self) -> None:
        """Stop the data collector.

        This method should:
        - Set running=False
        - Gracefully shut down any connections
        - Log the stop event
        """
        ...
