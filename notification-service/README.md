# Cartographer Notification Service

A microservice that handles notifications for network events and anomalies. Supports multiple notification channels (email via Resend, Discord) with ML-based anomaly detection.

## Features

### Notification Channels

1. **Email (via Resend)**
   - Beautiful HTML email templates
   - Plain text fallbacks
   - Customizable sender address
   - Uses the same Resend API as the auth service

2. **Discord**
   - Bot integration for server channels
   - Direct message support
   - Rich embeds with event details
   - Interactive buttons to view network map

### Anomaly Detection

The service includes a machine learning-based anomaly detector that:

- **Passively trains** on every health check to learn normal device behavior
- **Detects unexpected offline events** when a usually-online device goes down
- **Identifies latency spikes** that deviate significantly from the baseline
- **Flags packet loss anomalies** above normal thresholds
- **Learns time-based patterns** (hourly/daily availability patterns)

The ML model uses:
- Welford's online algorithm for real-time mean/variance calculation
- Z-score analysis for latency anomaly detection
- Historical pattern matching for time-based anomalies
- Configurable thresholds and sensitivity

### Notification Preferences

Users can configure:
- Enable/disable notifications globally
- Choose notification channels (email, Discord)
- Filter notification types (offline, online, anomaly, etc.)
- Set minimum priority threshold
- Configure quiet hours
- Set rate limits (max notifications per hour)

## Environment Variables

### Required (if using the feature)

| Variable | Description | Default |
|----------|-------------|---------|
| `RESEND_API_KEY` | Resend API key for email notifications | - |
| `DISCORD_BOT_TOKEN` | Discord bot token | - |
| `DISCORD_CLIENT_ID` | Discord application client ID | - |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `NOTIFICATION_DATA_DIR` | Directory for persisting data | `/app/data` |
| `EMAIL_FROM` | Email sender address | `Cartographer <notifications@cartographer.app>` |
| `APPLICATION_URL` | URL to the Cartographer app | `http://localhost:5173` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |

## API Endpoints

### Preferences

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/preferences` | Get user preferences |
| PUT | `/api/notifications/preferences` | Update user preferences |
| DELETE | `/api/notifications/preferences` | Reset preferences to default |

### Service Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/status` | Get service status and available channels |

### Discord Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/discord/info` | Get bot info and invite URL |
| GET | `/api/notifications/discord/guilds` | List servers the bot is in |
| GET | `/api/notifications/discord/guilds/{id}/channels` | List channels in a server |
| GET | `/api/notifications/discord/invite-url` | Get bot invite URL |

### Testing

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/notifications/test` | Send a test notification |

### History & Stats

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/history` | Get notification history |
| GET | `/api/notifications/stats` | Get notification statistics |

### ML / Anomaly Detection

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/ml/status` | Get ML model status |
| GET | `/api/notifications/ml/baseline/{ip}` | Get learned baseline for device |
| POST | `/api/notifications/ml/feedback/false-positive` | Mark detection as false positive |
| DELETE | `/api/notifications/ml/baseline/{ip}` | Reset baseline for device |
| DELETE | `/api/notifications/ml/reset` | Reset all ML data |

### Internal (for Health Service)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/notifications/process-health-check` | Process a health check result |

## Setting Up Discord Bot

1. **Create a Discord Application**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to the "Bot" section and create a bot
   - Copy the bot token

2. **Set Required Environment Variables**
   ```bash
   DISCORD_BOT_TOKEN=your_bot_token
   DISCORD_CLIENT_ID=your_client_id
   ```

3. **Invite the Bot to Your Server**
   - Use the invite URL from `/api/notifications/discord/invite-url`
   - Or construct it manually with permissions: Send Messages, Embed Links, Read Message History

4. **Configure Notification Preferences**
   - Enable Discord in your notification preferences
   - Select a server and channel, or enable DM delivery

## Notification Types

| Type | Description | Default Priority |
|------|-------------|------------------|
| `device_offline` | Device stopped responding | MEDIUM |
| `device_online` | Device came back online | LOW |
| `device_degraded` | Device has degraded performance | MEDIUM |
| `anomaly_detected` | ML detected anomalous behavior | HIGH |
| `high_latency` | Unusual latency spike | MEDIUM |
| `packet_loss` | Significant packet loss | MEDIUM |
| `isp_issue` | ISP/internet connectivity issue | HIGH |
| `security_alert` | Security-related alert | CRITICAL |
| `scheduled_maintenance` | Planned maintenance notice | LOW |
| `system_status` | System status update | LOW |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Notification Service                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    Email     │  │   Discord    │  │   Anomaly    │  │
│  │   Service    │  │   Service    │  │  Detector    │  │
│  │  (Resend)    │  │    (Bot)     │  │    (ML)      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                  │          │
│         └────────┬────────┴──────────────────┘          │
│                  │                                       │
│         ┌────────▼─────────┐                            │
│         │   Notification   │                            │
│         │     Manager      │                            │
│         │ (Rate Limiting,  │                            │
│         │  Preferences,    │                            │
│         │    Dispatch)     │                            │
│         └────────┬─────────┘                            │
│                  │                                       │
└──────────────────┼──────────────────────────────────────┘
                   │
          ┌────────▼────────┐
          │ Health Service  │
          │ (Health Checks) │
          └─────────────────┘
```

## ML Model Details

### Learning Algorithm

The anomaly detector uses several techniques:

1. **Welford's Online Algorithm** for computing running mean and variance without storing all data points

2. **Z-Score Analysis** for detecting latency anomalies:
   - Threshold: 3 standard deviations from mean
   - Adapts to each device's normal latency profile

3. **Time-Pattern Learning**:
   - Tracks availability by hour of day
   - Tracks availability by day of week
   - Detects deviations from expected patterns

4. **State Transition Tracking**:
   - Monitors online/offline transitions
   - Weights consecutive failures more heavily

### False Positive Handling

Users can mark anomalies as false positives via:
```
POST /api/notifications/ml/feedback/false-positive?event_id=xxx
```

This feedback is tracked and can be used to improve the model in future versions.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload

# Or with Docker
docker build -t cartographer-notifications .
docker run -p 8005:8005 cartographer-notifications
```

## Integration with Health Service

The health service should call the notification service after each health check:

```python
import httpx

async def report_health_check(device_ip, success, latency_ms, packet_loss, device_name, previous_state):
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8005/api/notifications/process-health-check",
            params={
                "device_ip": device_ip,
                "success": success,
                "latency_ms": latency_ms,
                "packet_loss": packet_loss,
                "device_name": device_name,
                "previous_state": previous_state,
            }
        )
```

This enables:
- Passive ML training on every health check
- Automatic anomaly detection
- Notification dispatch when appropriate

