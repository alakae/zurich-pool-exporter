# Sources: https://github.com/astral-sh/uv-docker-example and
# https://www.joshkasuboski.com/posts/distroless-python-uv/

# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:0.9.2-bookworm-slim AS builder
WORKDIR /code

# Enable bytecode compilation:
# https://docs.astral.sh/uv/reference/cli/#uv-sync--compile-bytecode
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
# https://docs.astral.sh/uv/reference/cli/#uv-sync--link-mode
ENV UV_LINK_MODE=copy

# Configure the Python directory so it is consistent
# https://docs.astral.sh/uv/reference/cli/#uv-python-install--install-dir
ENV UV_PYTHON_INSTALL_DIR=/python

# Only use the managed Python version
# https://docs.astral.sh/uv/reference/cli/#uv-python-install--managed-python
ENV UV_MANAGED_PYTHON=1

# Install Python before the project for caching
RUN --mount=type=cache,target=/root/.cache/uv \
      --mount=type=bind,source=.python-version,target=.python-version \
    uv python install

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
      --mount=type=bind,source=uv.lock,target=uv.lock \
      --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
        --mount=type=bind,source=uv.lock,target=uv.lock \
        --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
        --mount=type=bind,source=README.md,target=README.md \
    uv sync --locked --no-dev --no-editable

# Then, use a final image without uv
FROM gcr.io/distroless/base:debian12@sha256:4f6e739881403e7d50f52a4e574c4e3c88266031fd555303ee2f1ba262523d6a
WORKDIR /code

# Copy the Python version
COPY --from=builder --chown=python:python /python /python

# Copy the application from the builder
COPY --from=builder --chown=app:app /code/.venv /code/.venv

# Place executables in the environment at the front of the path
ENV PATH="/code/.venv/bin:$PATH"

CMD ["pool-exporter"]
