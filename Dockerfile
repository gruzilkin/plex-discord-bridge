FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project
COPY src/ src/
RUN uv sync --no-dev
EXPOSE 8080
CMD ["uv", "run", "plex-discord-bridge"]
