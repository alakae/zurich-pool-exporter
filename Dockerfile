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
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} pool_exporter ./pool_exporter

RUN devbox run -- poetry install --no-interaction --without dev

# Clean up
RUN nix-store --gc
RUN nix-store --optimise

CMD ["devbox", "run", "--", "python", "pool_exporter/main.py"]
