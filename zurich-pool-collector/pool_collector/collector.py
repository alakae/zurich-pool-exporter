from websockets import ClientConnection

import asyncio
import json
import logging
from typing import Dict, List, Optional

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from config import AppConfig
from metrics import PoolMetrics

logger = logging.getLogger(__name__)


class PoolDataCollector:
    """Collects data from the Zürich swimming pool WebSocket API."""

    def __init__(self, config: AppConfig, metrics: PoolMetrics):
        self.config = config
        self.metrics = metrics
        self.websocket_url = config.websocket.url
        self.retry_interval = config.websocket.retry_interval_seconds
        self.open_timeout = config.websocket.timeout_seconds
        self.ping_interval = config.websocket.ping_interval_seconds
        self.ping_timeout = config.websocket.ping_timeout_seconds
        self.running = False

    async def connect_websocket(self) -> ClientConnection | None:
        """Connect to the WebSocket API with retry logic."""
        while self.running:
            try:
                logger.info(f"Connecting to WebSocket API at {self.websocket_url}")
                websocket = await websockets.connect(
                    self.websocket_url,
                    ssl=True,
                    open_timeout=self.open_timeout,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                )
                logger.info("Successfully connected to WebSocket API")
                return websocket

            except WebSocketException as e:
                logger.error(f"Failed to connect to WebSocket: {e}")
                logger.info(f"Retrying in {self.retry_interval} seconds...")
                await asyncio.sleep(self.retry_interval)
        return None

    async def process_message(self, message: str) -> None:
        """Process incoming WebSocket message."""
        try:
            data = json.loads(message)
            if not isinstance(data, list):
                logger.warning(f"Unexpected data format: {message[:100]}")
                return

            # Update metrics for each pool
            for pool_data in data:
                self.metrics.update_pool_metrics(pool_data)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from message: {message[:100]}")
        except Exception as e:
            logger.exception(f"Error processing message: {e}")

    async def run(self) -> None:
        """Run the data collector loop."""
        self.running = True
        self.metrics.start_metrics_server()

        while self.running:
            websocket = await self.connect_websocket()
            if not websocket:
                logger.debug("No websocket connection available, continuing...")
                continue

            try:
                logger.info("Starting to receive messages from websocket")

                # Send the "all" command to request data for all pools
                logger.info("Sending 'all' command to server")
                await websocket.send("all")

                async for message in websocket:
                    message_str = str(message)
                    message_length = len(message_str)
                    logger.debug(f"Received message of length {message_length}")
                    await self.process_message(message_str)
            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error in WebSocket listener: {e}")
            finally:
                # Ensure connection is properly closed
                try:
                    await websocket.close()
                except:
                    pass

                if self.running:
                    logger.info(f"Reconnecting in {self.retry_interval} seconds...")
                    await asyncio.sleep(self.retry_interval)

    def stop(self) -> None:
        """Stop the data collector."""
        logger.info("Stopping data collector")
        self.running = False
