# see: https://github.com/docker/buildx/discussions/696
FROM --platform=${BUILDPLATFORM} jetpackio/devbox:latest AS requirements-export

# Build stage that generates requirements.txt from pyproject.toml
# We use devbox as base to avoid dependency version conflicts
WORKDIR /code
USER root:root
RUN mkdir -p /code && chown ${DEVBOX_USER}:${DEVBOX_USER} /code
USER ${DEVBOX_USER}:${DEVBOX_USER}
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} devbox.json devbox.json
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} devbox.lock devbox.lock

# Install devbox packages
RUN devbox install

# Copy only files needed for requirements.txt generation
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} pyproject.toml .
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} README.md .
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} src/pool_exporter ./src/pool_exporter

# Export production dependencies only
RUN devbox run -- poetry export --only=main --format=requirements.txt --output=requirements.txt

# Lightweight production image
FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Install production dependencies from previous stage
COPY --from=requirements-export /code/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL source files needed for installation
COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/

# Install the package itself
RUN pip install --no-deps .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /code
USER app

CMD ["python", "-m", "pool_exporter"]
