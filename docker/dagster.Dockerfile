FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy the whole uv workspace (root + all members) so `uv sync` can resolve it.
COPY pyproject.toml uv.lock* ./
COPY config ./config
COPY extraction ./extraction
COPY orchestration ./orchestration
COPY dbt_project ./dbt_project

RUN uv sync --package orchestration --frozen --no-dev || uv sync --package orchestration --no-dev

ENV DAGSTER_HOME=/app/dagster_home
COPY docker/dagster.yaml ${DAGSTER_HOME}/dagster.yaml

WORKDIR /app/orchestration
CMD ["uv", "run", "dagster", "dev", "-h", "0.0.0.0", "-p", "3000"]
