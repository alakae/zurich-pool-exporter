import asyncio
import logging
import signal
import sys

from pool_exporter.config import AppConfig, load_config
from pool_exporter.data_collector import DataCollector
from pool_exporter.metrics import PoolMetrics
from pool_exporter.occupancy_collector import OccupancyCollector
from pool_exporter.temperature_collector import TemperatureCollector


def setup_logging(config: AppConfig) -> logging.Logger:
    """Configure logging and return logger instance."""
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format=config.logging.format,
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Zürich Pool Data Collector")
    return logger


def setup_signal_handlers(
    collectors: tuple[DataCollector, ...],
    shutdown_event: asyncio.Event,
    logger: logging.Logger,
) -> None:
    """Set up signal handlers for graceful shutdown."""

    def handle_signal(sig: int, frame: object) -> None:
        logger.info(f"Received signal {sig}, shutting down...")
        for collector in collectors:
            collector.stop()
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


async def run_collectors_with_shutdown(
    collectors: tuple[DataCollector, ...],
    shutdown_event: asyncio.Event,
    logger: logging.Logger,
) -> None:
    """Run collectors and handle graceful shutdown."""
    # Create tasks for the collectors
    tasks = [asyncio.create_task(collector.run()) for collector in collectors]
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    try:
        # Wait for either all tasks to complete or shutdown signal
        done, pending = await asyncio.wait(
            tasks + [shutdown_task],
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
        # Ensure all collector tasks are cancelled
        for task in tasks:
            if not task.done():
                task.cancel()
        logger.info("Pool Data Collector stopped")


async def run_exporter() -> None:
    """Main entry point for the pool data collector."""
    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    logger = setup_logging(config)

    # Initialize metrics
    metrics = PoolMetrics(config)
    metrics.start_metrics_server()

    # Create collectors
    collectors = (
        OccupancyCollector(config, metrics),
        TemperatureCollector(config, metrics),
    )

    # Create shutdown event and setup signal handlers
    shutdown_event = asyncio.Event()
    setup_signal_handlers(collectors, shutdown_event, logger)

    # Run collectors with shutdown handling
    await run_collectors_with_shutdown(collectors, shutdown_event, logger)


def run() -> None:
    asyncio.run(run_exporter())
