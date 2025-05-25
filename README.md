# Zürich Pool Exporter

A data collection service that monitors real-time occupancy and temperature data for public swimming pools in Zürich, Switzerland and exposes metrics in Prometheus format.

## Overview

This project collects data from Zürich's swimming pools through:

- Real-time occupancy data via WebSocket connection
- Temperature data via HTTP polling
- Exposes metrics in Prometheus format for monitoring and visualization

## Example

```
# HELP zurich_pools_current_fill Current number of visitors at the pool
# TYPE zurich_pools_current_fill gauge
zurich_pools_current_fill{pool_name="Freibad Seebach",pool_uid="SSD-11"} 4.0
zurich_pools_current_fill{pool_name="Hallenbad Oerlikon",pool_uid="SSD-7"} 69.0
# HELP zurich_pools_water_temperature Water temperature of the pool in degrees Celsius
# TYPE zurich_pools_water_temperature gauge
zurich_pools_water_temperature{pool_name="Hallenbad Oerlikon",pool_uid="SSD-7"} 28.0
zurich_pools_water_temperature{pool_name="Freibad Seebach",pool_uid="SSD-11"} 23.0
```

## Development

### Using Devbox (recommended)

This project uses [Devbox](https://jetify.com/devbox/) for development environment setup:

```shell script
# Install Devbox (if not already installed)
# Then, activate the development environment:
devbox shell
```

This will automatically:

- Set up Python 3.13
- Configure Poetry
- Install all dependencies
- Set up the virtual environment

## Usage

### Development

```shell script
# Start the development environment
devbox shell

# Run the exporter
devbox run run
```

### Development Commands

```shell script
# Run type checking
devbox run mypy

# Format code
devbox run black
devbox run isort
devbox run mdformat

# Build container
devbox run docker-build

# Run tests
devbox run test
```

### Local Testing with Prometheus and Grafana

Run the dockerized exporter locally together with Grafana and Prometheus
for testing.

```shell script
# Build and start services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```
