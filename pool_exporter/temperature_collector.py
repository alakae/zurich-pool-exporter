import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import aiohttp
from api_types import TemperatureData
from config import AppConfig
from metrics import PoolMetrics

logger = logging.getLogger(__name__)


class TemperatureCollector:
    """Collects temperature data from the Zürich swimming pool XML API."""

    def __init__(self, config: AppConfig, metrics: PoolMetrics):
        self.config = config
        self.metrics = metrics
        self.xml_url = config.temperature.url
        self.poll_interval = config.temperature.poll_interval_seconds
        self.timeout = config.temperature.timeout_seconds
        self.running = False
        self._publish_hard_coded()

    async def fetch_temperature_data(self) -> Optional[str]:
        """Fetch temperature data from the XML API."""
        try:
            logger.info(f"Fetching temperature data from {self.xml_url}")
            timeout = aiohttp.ClientTimeout(total=self.timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.xml_url) as response:
                    if response.status != 200:
                        logger.error(
                            f"Failed to fetch temperature data: HTTP {response.status}"
                        )
                        return None

                    return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching temperature data: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error fetching temperature data: {e}")
            return None

    def parse_temperature_data(self, xml_data: str) -> list[TemperatureData]:
        """Parse temperature data from XML response."""
        try:
            logger.debug("Starting to parse XML temperature data")
            root = ET.fromstring(xml_data)
            pool_data = []

            pools = root.findall(".//bath")
            logger.debug(f"Found {len(pools)} bath entries in XML")
            for pool in pools:
                pool_id = pool.find("poiid")
                title = pool.find("title")
                temperature = pool.find("temperatureWater")
                status = pool.find("openClosedTextPlain")
                date_modified = pool.find("dateModified")

                if (
                    pool_id is not None
                    and temperature is not None
                    and title is not None
                ):
                    pool_id_text = pool_id.text.lower() if pool_id.text else None
                    pool_title_text = title.text.strip() if title.text else ""
                    logger.debug(
                        f"Processing pool with ID: {pool_id_text} and name: {pool_title_text}"
                    )

                    try:
                        temp_value = int(temperature.text) if temperature.text else None
                        logger.debug(
                            f"Temperature value for pool {pool_id_text}: {temp_value}"
                        )

                        pool_data.append(
                            TemperatureData(
                                pool_id=pool_id_text,
                                title=title.text,
                                temperature=temp_value,
                                status=(
                                    status.text
                                    if status is not None and status.text
                                    else "Unknown"
                                ),
                                last_updated=(
                                    date_modified.text
                                    if date_modified is not None and date_modified.text
                                    else None
                                ),
                            )
                        )
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Could not parse temperature for pool {pool_id_text}: {e}"
                        )

            logger.debug(f"Successfully parsed data for {len(pool_data)} pools")
            return pool_data
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML data: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error parsing XML data: {e}")
            return []

    def update_metrics(self, pool_data: list[TemperatureData]) -> None:
        for pool in pool_data:
            self.metrics.update_temperature_metrics(pool)

    async def collect(self) -> None:
        """Collect temperature data and update metrics."""
        xml_data = await self.fetch_temperature_data()
        if xml_data:
            pool_data = self.parse_temperature_data(xml_data)
            if pool_data:
                logger.info(
                    f"Successfully collected temperature data for {len(pool_data)} pools"
                )
                self.update_metrics(pool_data)
            else:
                logger.warning("No temperature data was parsed from the XML response")
        else:
            logger.warning("Failed to fetch temperature data")

    async def run(self) -> None:
        """Run the temperature collector."""
        self.running = True

        logger.info(
            f"Temperature collector started with polling interval of {self.poll_interval} seconds"
        )

        while self.running:
            try:
                await self.collect()
            except Exception as e:
                logger.exception(f"Error in temperature collector: {e}")

            if self.running:
                logger.debug(
                    f"Waiting {self.poll_interval} seconds until next temperature collection"
                )
                await asyncio.sleep(self.poll_interval)

        logger.info("Temperature collector stopped")

    def stop(self) -> None:
        """Stop the temperature collector."""
        logger.info("Stopping temperature collector")
        self.running = False

    def _publish_hard_coded(self) -> None:
        for pool in self.config.pools:
            if not pool.hardcoded_temperatur:
                continue
            data = TemperatureData(
                pool_id=pool.uid,
                title=pool.name,
                temperature=pool.hardcoded_temperatur,
            )
            self.metrics.update_temperature_metrics(data)
