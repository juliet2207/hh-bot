# syntax=docker/dockerfile:1

# ===== Stage 1: build with uv =====
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential libffi-dev libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -Ls https://astral.sh/uv/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"

# Copy dependency files and install (no dev deps)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source (only source files)
COPY . .

# ===== Stage 2: slim runtime =====
FROM python:3.11-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# Runtime libs only — no heavy dev headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy app and virtualenv
COPY --from=builder /app /app

# Remove build caches
RUN rm -rf /app/.cache /root/.cache

# Copy uv CLI (optional but handy)
COPY --from=builder /root/.local/bin/uv /usr/local/bin/uv

EXPOSE 8271

CMD ["uv", "run", "main.py"]