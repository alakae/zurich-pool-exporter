# Zürich Pool Exporter

[![Built with Devbox](https://www.jetify.com/img/devbox/shield_galaxy.svg)](https://www.jetify.com/devbox/docs/contributor-quickstart/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://kentcdodds.github.io/makeapullrequest.com/)

> A data collection service that monitors real-time occupancy and temperature data for public swimming pools in Zürich, Switzerland and exposes metrics in Prometheus format.

This is a just for fun project.

## Overview

This project collects data from Zürich's swimming pools through:

- Real-time occupancy data via WebSocket connection
- Temperature data via HTTP polling
- Exposes metrics in Prometheus format for monitoring and visualization

## Disclaimer

This project is an independent, open-source initiative and is **not**
affiliated with, endorsed by, or associated with the City of Zürich,
the Sportamt Zürich, or any of their agencies.
All code provided by this project is for informational purposes only.

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

- Set up Python
- Set up the virtual environment
- Install tools such as uv and ruff

## Usage

### Building and Installing Locally

```shell script
# Build a wheel locally and install using pipx
devbox run build
PIPX_DEFAULT_PYTHON=/usr/local/bin/python3.13 pipx install dist/pool_exporter-*.whl 
```

### Development

```shell script
# Start the development environment
devbox shell

# Run the exporter locally from an editable install 
devbox run serve
curl http://localhost:8000/metrics
```

### Development Commands

```shell script
# Run type checking
devbox run mypy

# Format code
devbox run format
devbox run check
devbox run mdformat
devbox run dprint fmt

# Export the lockfile in `requirements-txt` format
devbox run build

# Build wheel into /dist
devbox run build

# Build container
devbox run docker-build

# Wipe temporary files
devbox run clear

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
