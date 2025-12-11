# ─────────────────────────────────────────────────────────────────────────────
# Cartographer Auth Service
# User authentication and authorization microservice
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System packages (minimal for auth service, with retry for transient network issues)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    for i in 1 2 3; do \
        apt-get update && break || sleep 5; \
    done && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates

# Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Application code
COPY app/ /app/app/

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/healthz || exit 1

EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
