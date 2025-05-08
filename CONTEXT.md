# Zürich Swimming Pool Occupancy Dashboard Specification

## Project Overview
This project aims to create a real-time dashboard displaying visitor numbers for swimming pools in Zürich. The system will collect data from the city's public API, store it in Prometheus, and visualize it through Grafana dashboards.

## Data Source
- **API Endpoint**: `wss://badi-public.crowdmonitor.ch:9591/api`
- **Protocol**: WebSocket
- **Authentication**: None required
- **Data Format**: JSON array of pool objects
- **Sample Response**:
  ```json
  [
    {
      "uid": "SSD-11",
      "name": "Freibad Seebach",
      "freespace": 1985,
      "maxspace": 2000,
      "currentfill": "15"
    },
    {
      "uid": "SSD-7",
      "name": "Hallenbad Oerlikon",
      "freespace": 1000,
      "maxspace": 1000,
      "currentfill": "0"
    }
  ]
  ```

## Metrics to Collect
For each configured swimming pool:
1. `currentfill` - Current number of visitors
2. `freespace` - Available capacity remaining
3. `maxspace` - Maximum capacity of the pool
4. Calculated percentage occupancy (`currentfill / maxspace * 100`)

## System Architecture

### Components
1. **Data Collector**
    - Python script that connects to the WebSocket API
    - Transforms JSON data into Prometheus metrics
    - Exposes metrics via HTTP endpoint

2. **Prometheus**
    - Scrapes metrics from the collector every 15 minutes
    - Stores time-series data
    - Provides query interface for Grafana

3. **Grafana**
    - Connects to Prometheus as a data source
    - Displays dashboards with pool occupancy metrics
    - Provides historical views and current status

### Data Flow
1. Data Collector connects to WebSocket API
2. Collector transforms data to Prometheus format
3. Prometheus scrapes metrics from Collector
4. Grafana queries Prometheus and displays visualizations

## Technical Requirements

### Data Collector
- **Language**: Python 3.9+
- **Key Libraries**:
    - `websockets` for WebSocket connection
    - `prometheus_client` for metrics exposition
    - `asyncio` for asynchronous processing
- **Configuration**:
    - List of pool UIDs to monitor (configurable)
    - Metrics endpoint port (default: 8000)
    - Logging level

### Prometheus
- **Version**: 2.40+
- **Configuration**:
    - Scrape interval: 15 minutes
    - Retention period: 15 days (default)
    - Target: Data Collector metrics endpoint

### Grafana
- **Version**: 9.0+
- **Dashboards**:
    1. Overview dashboard with:
        - Gauges showing current occupancy percentage for each pool
        - Traffic light indicators (Green: 80%)
    2. Detailed dashboard with:
        - Time-series graphs showing occupancy trends
        - Current visitor counts
        - Available capacity

## Deployment
- **Containerization**: Docker with docker-compose
- **Container Images**:
    - Custom Python image for Data Collector
    - Official Prometheus image
    - Official Grafana image
- **Persistence**:
    - Docker volumes for Prometheus and Grafana data
- **Networking**:
    - Internal network for component communication
    - Exposed ports:
        - Grafana: 3000
        - Prometheus: 9090 (optional)

## Configuration Files

### docker-compose.yml
Will define:
- All three services (collector, prometheus, grafana)
- Volume mounts for persistence
- Network configuration
- Environment variables

### prometheus.yml
Will define:
- Scrape configuration for the collector
- Global settings

### collector_config.yml
Will define:
- Pool UIDs to monitor
- WebSocket connection parameters
- Metrics exposition settings

## Implementation Phases
1. **Setup**: Create Docker Compose environment
2. **Data Collection**: Implement WebSocket client and Prometheus metrics
3. **Storage**: Configure Prometheus scraping
4. **Visualization**: Create Grafana dashboards
5. **Testing & Refinement**: Verify data accuracy and dashboard usability

## Notes
- The system will be designed to handle connection interruptions gracefully
- The collector will validate and sanitize data before exposing metrics
- All components will be configured with appropriate logging
- The solution prioritizes simplicity and reliability
