FROM jetpackio/devbox:latest

# Installing your devbox project
WORKDIR /code
USER root:root
RUN mkdir -p /code && chown ${DEVBOX_USER}:${DEVBOX_USER} /code
USER ${DEVBOX_USER}:${DEVBOX_USER}
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} devbox.json devbox.json
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} devbox.lock devbox.lock

# Install devbox packages
RUN devbox install

# Copy project files including pyproject.toml
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} pyproject.toml .
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} README.md .
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} pool_collector ./pool_collector

# Install dependencies with Poetry (without creating a virtual environment)
RUN devbox run -- poetry config virtualenvs.create false \
    && devbox run -- poetry install --no-interaction --without dev

# Clean up
RUN nix-store --gc
RUN nix-store --optimise

CMD ["devbox", "run", "--", "poetry", "run", "python", "pool_collector/main.py"]
