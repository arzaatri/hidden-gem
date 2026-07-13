FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy the whole uv workspace (root + all members) so `uv sync` can resolve it.
COPY pyproject.toml uv.lock* ./
COPY config ./config
COPY backend ./backend

RUN uv sync --package backend --frozen --no-dev || uv sync --package backend --no-dev

WORKDIR /app/backend
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
