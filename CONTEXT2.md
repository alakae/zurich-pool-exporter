# Pool Temperature Collection - Architecture Document
## Feature Overview
This document outlines the integration of swimming pool temperature data into the existing Zürich Swimming Pool Occupancy system. The system will be enhanced to:
1. Collect temperature data from the XML API endpoint
2. Process and expose temperature metrics alongside existing occupancy metrics
3. Update the collection process to poll both data sources at appropriate intervals

## Data Source Details
**XML API Endpoint**: `https://www.stadt-zuerich.ch/stzh/bathdatadownload`
**Data Format**: XML containing pool information including:
- Pool title (`<title>`)
- Water temperature (`<temperatureWater>`)
- Pool ID (`<poiid>`) - Matches existing IDs (in lowercase)
- Last updated timestamp (`<dateModified>`)
- Open/closed status (`<openClosedTextPlain>`)

## Architecture Changes
### 1. Configuration Updates
#### New Configuration Class
Add a `TemperatureConfig` class to for the XML API settings: `config.py`
- URL endpoint
- Polling interval (hourly)
- HTTP request timeout

#### Configuration File Updates
Extend with a new section for temperature-related settings. `config.yml`
### 2. Temperature Collector Component
Create a new module `temperature_collector.py` that will:
- Poll the XML API at the configured interval
- Parse the XML response
- Map the temperature data to the existing pool configuration
- Provide the processed data to the metrics system

### 3. Metrics Extensions
Extend to: `metrics.py`
- Add a new Prometheus gauge for water temperature
- Include update methods for temperature metrics

### 4. Collector Coordination
Update the main application flow to:
- Initialize both collectors on startup
- Manage the different polling schedules
- Handle errors independently for each data source

## Implementation Details
### 1. Configuration Updates
``` python
# Added to config.py
@dataclass
class TemperatureConfig:
    url: str
    poll_interval_seconds: int  # Default: 3600 (1 hour)
    timeout_seconds: int
```
Include this in the class and update the YAML loader. `AppConfig`
### 2. Temperature Collector Implementation
Create a new `TemperatureCollector` class with:
- HTTP request functionality (using `aiohttp` or similar)
- XML parsing (using `xml.etree.ElementTree` or similar)
- Mapping logic to correlate XML pool IDs with existing configuration
- Polling mechanism with configured interval
- Error handling and retry logic

### 3. Metrics Integration
Add a new temperature gauge to the class: `PoolMetrics`
``` python
self.water_temperature = Gauge(
    f"{self.namespace}_water_temperature",
    "Water temperature of the pool in degrees Celsius",
    ["pool_uid", "pool_name"],
)
```
Add a temperature update method that will be called by the temperature collector.
### 4. Integration Points
#### Main Application Flow
- Initialize both collectors at startup
- Run them concurrently using asyncio tasks
- Handle graceful shutdown for both collectors

#### Error Handling
- Each collector should handle its own errors
- Failures in one collector should not affect the other
- Log appropriate messages for monitoring

## Technology Selection
- **HTTP Client**: `aiohttp` (asynchronous, compatible with existing asyncio architecture)
- **XML Parsing**: Python's built-in `xml.etree.ElementTree` (sufficient for the simple XML structure)
- **Scheduling**: Use tasks and sleep for simple polling `asyncio`

## Data Flow
1. Temperature collector polls the XML API endpoint at hourly intervals
2. XML response is parsed to extract temperature data
3. Pool IDs are mapped between XML `poiid` and configuration values `uid`
4. Temperature data is passed to the metrics system
5. Prometheus scrapes the updated metrics endpoint
6. Grafana displays the combined metrics

## Implementation Plan
1. **Configuration Updates**:
    - Add temperature configuration classes
    - Update YAML configuration

2. **Temperature Collection**:
    - Implement XML API client
    - Create parsing and mapping logic
    - Set up polling mechanism

3. **Metrics Integration**:
    - Add temperature gauge
    - Implement update methods

4. **Coordination**:
    - Update main application to manage both collectors
    - Implement error handling and logging

5. **Testing**:
    - Verify XML parsing with sample data
    - Test polling mechanisms
    - Validate metrics exposure
    - Confirm system resilience to API failures

## Considerations
- **Error Handling**: The temperature API may have different availability patterns than the WebSocket API
- **Data Freshness**: Temperature data may be updated less frequently than occupancy data
- **Pool ID Mapping**: Need to ensure correct correlation between the two data sources
- **XML Validation**: Should validate the XML structure before processing
- **Cache Control**: Consider if caching temperature data is appropriate given its update frequency

This architecture maintains the existing system's asynchronous and event-driven approach while extending it to handle the new data source with appropriate polling intervals.
