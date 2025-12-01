# Cartographer Health Service

A microservice for monitoring the health and availability of network devices discovered by Cartographer.

## Features

- **ICMP Ping Checks**: Latency, packet loss, jitter measurements
- **DNS Resolution**: Reverse DNS lookups and hostname resolution
- **Port Scanning**: Detection of common open ports (SSH, HTTP, HTTPS, SMB, etc.)
- **Historical Statistics**: 24-hour uptime and latency tracking
- **Batch Operations**: Check multiple devices in parallel

## Running Standalone

### With Python

```bash
cd health-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### With Docker

```bash
cd health-service
docker build -t cartographer-health .
docker run -p 8001:8001 --cap-add NET_RAW cartographer-health
```

> Note: The `NET_RAW` capability is required for ICMP ping operations.

## API Endpoints

### Health Checks

- `GET /api/health/check/{ip}` - Check single device health
  - Query params: `include_ports` (bool), `include_dns` (bool)
  
- `POST /api/health/check/batch` - Check multiple devices
  ```json
  {
    "ips": ["192.168.1.1", "192.168.1.2"],
    "include_ports": false,
    "include_dns": true
  }
  ```

### Individual Operations

- `GET /api/health/ping/{ip}` - Quick ping test
- `GET /api/health/ports/{ip}` - Scan common ports
- `GET /api/health/dns/{ip}` - DNS lookup

### Cache

- `GET /api/health/cached/{ip}` - Get cached metrics
- `GET /api/health/cached` - Get all cached metrics
- `DELETE /api/health/cache` - Clear cache

## Response Example

```json
{
  "ip": "192.168.1.1",
  "status": "healthy",
  "last_check": "2024-01-15T10:30:00Z",
  "ping": {
    "success": true,
    "latency_ms": 1.5,
    "packet_loss_percent": 0,
    "min_latency_ms": 1.2,
    "max_latency_ms": 2.1,
    "avg_latency_ms": 1.5,
    "jitter_ms": 0.3
  },
  "dns": {
    "success": true,
    "resolved_hostname": "router.local",
    "reverse_dns": "router.lan"
  },
  "open_ports": [
    {"port": 80, "open": true, "service": "HTTP", "response_time_ms": 5.2}
  ],
  "uptime_percent_24h": 99.9,
  "avg_latency_24h_ms": 1.8,
  "checks_passed_24h": 1440,
  "checks_failed_24h": 1
}
```

## Health Status Values

- `healthy` - Device responding with acceptable latency
- `degraded` - Device responding but with high latency or packet loss
- `unhealthy` - Device not responding
- `unknown` - Unable to determine status

## Environment Variables

- `CORS_ORIGINS` - Comma-separated list of allowed CORS origins (default: `*`)

## Running with Docker Compose

From the project root:

```bash
docker-compose up --build
```

This will start both the main Cartographer app and the health service.

