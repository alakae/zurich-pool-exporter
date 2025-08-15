import asyncio
import logging
import signal
import sys

from pool_exporter.config import load_config
from pool_exporter.metrics import PoolMetrics
from pool_exporter.occupancy_collector import OccupancyCollector
from pool_exporter.temperature_collector import TemperatureCollector


async def run_exporter() -> None:
    """Main entry point for the pool data collector."""
    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format=config.logging.format,
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Zürich Pool Data Collector")

    # Initialize metrics
    metrics = PoolMetrics(config)
    metrics.start_metrics_server()

    # Create collectors
    occupancy_collector = OccupancyCollector(config, metrics)
    temperature_collector = TemperatureCollector(config, metrics)

    # Create a shutdown event for graceful termination
    shutdown_event = asyncio.Event()

    # Set up signal handlers for graceful shutdown
    def handle_signal(sig: int, frame: object) -> None:
        logger.info(f"Received signal {sig}, shutting down...")
        occupancy_collector.stop()
        temperature_collector.stop()
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Create tasks for the collectors
    occupancy_task = asyncio.create_task(occupancy_collector.run())
    temperature_task = asyncio.create_task(temperature_collector.run())

    try:
        # Wait for either all tasks to complete or shutdown signal
        done, pending = await asyncio.wait(
            [
                occupancy_task,
                temperature_task,
                asyncio.create_task(shutdown_event.wait()),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # If shutdown was requested, cancel pending tasks
        if shutdown_event.is_set():
            logger.info("Shutdown requested, cancelling tasks...")
            for task in pending:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete cancellation
            if pending:
                await asyncio.wait(pending, timeout=5.0)

    except asyncio.CancelledError:
        logger.info("Tasks were cancelled")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        # Ensure all tasks are cancelled
        for task in [occupancy_task, temperature_task]:
            if not task.done():
                task.cancel()
        logger.info("Pool Data Collector stopped")


def run() -> None:
    asyncio.run(run_exporter())
