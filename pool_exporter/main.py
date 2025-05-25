import asyncio
import logging
import signal
import sys

from config import load_config
from metrics import PoolMetrics
from occupancy_collector import OccupancyCollector
from temperature_collector import TemperatureCollector


async def main() -> None:
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

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        occupancy_collector.stop()
        temperature_collector.stop()
        # Give tasks a chance to complete
        loop.call_later(1, loop.stop)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Run collectors concurrently
    try:
        await asyncio.gather(
            occupancy_collector.run(),
            temperature_collector.run(),
        )
    except asyncio.CancelledError:
        logger.info("Tasks were cancelled")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        logger.info("Pool Data Collector stopped")


if __name__ == "__main__":
    asyncio.run(main())
