# see: https://github.com/docker/buildx/discussions/696
FROM --platform=${BUILDPLATFORM} jetpackio/devbox:latest AS builder

# Build stage that generates requirements.txt and wheel
# We use devbox as base to avoid dependency version conflicts
WORKDIR /code
USER root:root
RUN mkdir -p /code && chown ${DEVBOX_USER}:${DEVBOX_USER} /code
USER ${DEVBOX_USER}:${DEVBOX_USER}
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} devbox.json devbox.json
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} devbox.lock devbox.lock

# Install devbox packages
RUN devbox install

# Copy ALL files needed for wheel building and requirements.txt generation
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} pyproject.toml .
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} README.md .
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} src/ ./src/

# Export EXACT versions from lock file
RUN devbox run -- poetry export --only=main --format=requirements.txt --output=requirements.txt

# Build the wheel
RUN devbox run build

# Lightweight production image
FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Install production dependencies with EXACT versions from lock file
COPY --from=builder /code/requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Install the wheel WITHOUT dependencies (they're already installed)
COPY --from=builder /code/dist/*.whl /tmp/
RUN python -m pip install --no-cache-dir --no-deps /tmp/*.whl

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /code
USER app

CMD ["python", "-m", "pool_exporter"]
