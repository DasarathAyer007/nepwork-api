# Builder Stage
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies required to build Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for Docker cache optimization
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Install dependencies only
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY . .

# Install project
RUN uv sync --frozen --no-dev


# Runtime Stage
FROM python:3.14-slim AS runtime


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app


# Runtime dependencies for Django GIS/PostGIS
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    proj-bin \
    proj-data \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy virtual environment
COPY --from=builder /app/.venv /app/.venv

# Copy application
COPY --chown=appuser:appuser . .


USER appuser

EXPOSE 8000


# Render provides environment variables at runtime
# collectstatic runs after SECRET_KEY/DATABASE_URL are available
CMD ["sh", "-c", "python manage.py collectstatic --noinput && exec daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application"]
