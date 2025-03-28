FROM python:3.13.0-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local

# Install system dependencies required for mysql-connector
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Layer uvx
COPY --from=ghcr.io/astral-sh/uv:0.6.9 /uv /uvx /bin/

# Install dependencies using uv
RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

EXPOSE 8000
CMD ["uvicorn", "--app-dir", "/app", "app:app", "--host", "0.0.0.0", "--port", "8000"]
