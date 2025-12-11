# ─────────────────────────────────────────────────────────────────────────────
# Cartographer Notification Service
# Handles email, Discord, and other notification channels
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies (with retry for transient network issues)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    for i in 1 2 3; do \
        apt-get update && break || sleep 5; \
    done && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8005/healthz || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]

