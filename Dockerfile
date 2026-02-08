# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Build frontend (Vue 3 + Vite)
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-bookworm AS frontend-builder
WORKDIR /app

# Build argument for base path (default: / for standalone, /app/ for cloud)
ARG VITE_BASE_PATH=/

# Install dependencies and build
COPY frontend/package.json frontend/package-lock.json* ./frontend/
WORKDIR /app/frontend
RUN npm ci || npm install
COPY frontend/ /app/frontend/

# Build with the specified base path
ENV VITE_BASE_PATH=${VITE_BASE_PATH}
RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Backend runtime with network tooling
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS backend
ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

# System packages for network mapping (with retry for transient network issues)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
	--mount=type=cache,target=/var/lib/apt,sharing=locked \
	for i in 1 2 3; do \
		apt-get update && break || sleep 5; \
	done && \
	apt-get install -y --no-install-recommends \
		arp-scan \
		nmap \
		snmp \
		snmpd \
		libsnmp-base \
		dnsutils \
		avahi-utils \
		lldpd \
		traceroute \
		fping \
		iproute2 \
		bash \
		ca-certificates \
		procps \
		curl \
		samba-client && \
	echo "mibs :" > /etc/snmp/snmp.conf

# Python deps
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# App source
COPY backend/ /app/backend/
COPY lan_mapper.sh /app/lan_mapper.sh
RUN chmod +x /app/lan_mapper.sh

# Frontend dist built in Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Serve the built frontend via FastAPI StaticFiles
ENV FRONTEND_DIST=/app/frontend/dist

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Volume for persistent data
VOLUME ["/app/data"]

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
