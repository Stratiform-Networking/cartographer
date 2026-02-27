# Cartographer Load Tests

This directory contains load testing scripts for all Cartographer microservices using [Locust](https://locust.io/), a modern Python-based load testing framework.

## Quick Start

```bash
# Install dependencies
cd load-tests
pip install -r requirements.txt

# Run a quick test on all services (provide your Cartographer credentials)
python run_load_tests.py -s all -u 10 -r 2 -t 60 --username YOUR_USERNAME --password YOUR_PASSWORD

# Or using environment variables
export LOADTEST_USERNAME=your_username
export LOADTEST_PASSWORD=your_password
export LOADTEST_AUTH_HOST=http://localhost:8002
python run_load_tests.py -s all -u 10 -r 2 -t 60

# Windows PowerShell:
$env:LOADTEST_USERNAME="your_username"
$env:LOADTEST_PASSWORD="your_password"
$env:LOADTEST_AUTH_HOST="http://localhost:8002"
python run_load_tests.py -s all -u 10 -r 2 -t 60

# Or open the web UI for interactive testing
python run_load_tests.py -s all --web --username YOUR_USERNAME --password YOUR_PASSWORD
```

## ⚠️ Authentication Required

**All Cartographer API endpoints require JWT authentication.** You must provide valid credentials:

### Option 1: Command Line Arguments (Quick Testing)
```bash
python run_load_tests.py -s all --username myuser --password mypass

# If testing a non-proxy service directly, point auth to auth-service
python run_load_tests.py -s metrics --host http://localhost:8003 \
  --auth-host http://localhost:8002 --username myuser --password mypass
```

### Option 2: Environment Variables (Recommended for CI/CD)
```bash
# Linux/Mac
export LOADTEST_USERNAME=your_username
export LOADTEST_PASSWORD=your_password
export LOADTEST_AUTH_HOST=http://localhost:8002

# Windows Command Prompt
set LOADTEST_USERNAME=your_username
set LOADTEST_PASSWORD=your_password

# Windows PowerShell
$env:LOADTEST_USERNAME="your_username"
$env:LOADTEST_PASSWORD="your_password"
$env:LOADTEST_AUTH_HOST="http://localhost:8002"
```

### Option 3: Using Locust Directly
```bash
LOADTEST_USERNAME=user LOADTEST_PASSWORD=pass locust -f locustfile_all.py --host=http://localhost:8000
```

## Services

| Service | Port | Locustfile | Description |
|---------|------|------------|-------------|
| Health | 8001 | `locustfile_health.py` | Health monitoring, ping, DNS, speed tests |
| Auth | 8002 | `locustfile_auth.py` | Authentication, users, invitations |
| Metrics | 8003 | `locustfile_metrics.py` | Network snapshots, Redis pub/sub |
| Assistant | 8004 | `locustfile_assistant.py` | AI chat, providers, context |
| Notifications | 8005 | `locustfile_notification.py` | Alerts, Discord, ML anomaly detection |
| All | 8000 | `locustfile_all.py` | Combined test via backend proxy |

## Usage

### Using the Runner Script

The `run_load_tests.py` script provides an easy interface:

```bash
# Test individual service
python run_load_tests.py -s health -u 20 -r 5 -t 120 --auth-host http://localhost:8002

# Test all services through the main proxy
python run_load_tests.py -s all -u 50 -r 10 -t 300

# Open web UI for interactive testing
python run_load_tests.py -s metrics --web

# Generate HTML report
python run_load_tests.py -s all -u 30 -r 5 -t 180 --html report.html

# Test only read operations
python run_load_tests.py -s health --tags read -u 100 -r 20 -t 60

# Custom host
python run_load_tests.py -s all --host http://192.168.1.100:8000 --auth-host http://192.168.1.100:8002 -u 20 -t 60
```

### Using Locust Directly

```bash
# Single service
LOADTEST_AUTH_HOST=http://localhost:8002 locust -f locustfile_health.py --host=http://localhost:8001

# Headless mode
LOADTEST_AUTH_HOST=http://localhost:8002 locust -f locustfile_metrics.py --host=http://localhost:8003 \
    --headless -u 50 -r 5 -t 5m --exit-code-on-error 1

# With specific tags
LOADTEST_AUTH_HOST=http://localhost:8002 locust -f locustfile_auth.py --host=http://localhost:8002 \
    --tags auth,read --headless -u 20 -r 2 -t 2m --exit-code-on-error 1
```

## Test Categories (Tags)

Each test is tagged for selective execution:

### By Operation Type
- `read` - Read-only operations (GET requests)
- `write` - Write operations (POST, PUT, DELETE)

### By Feature
- `health-check` - Device health checking
- `monitoring` - Background monitoring
- `gateway` - Gateway/ISP features
- `speedtest` - Speed test endpoints
- `auth` - Authentication
- `users` - User management
- `invites` - Invitation system
- `snapshot` - Network snapshots
- `config` - Configuration
- `providers` - AI providers
- `context` - Network context
- `chat` - AI chat (⚠️ costs money!)
- `preferences` - Notification preferences
- `discord` - Discord integration
- `ml` - Machine learning/anomaly detection
- `scheduled` - Scheduled broadcasts
- `system` - Health checks

## Test Scenarios

### 1. Baseline Performance Test
Quick test to establish baseline metrics:
```bash
python run_load_tests.py -s all -u 10 -r 2 -t 60
```

### 2. Sustained Load Test
Test service stability under moderate load:
```bash
python run_load_tests.py -s all -u 50 -r 5 -t 600 --html sustained_load.html
```

### 3. Spike Test
Test service behavior under sudden load spikes:
```bash
python run_load_tests.py -s all -u 200 -r 50 -t 120
```

### 4. Read-Heavy Workload
Simulate dashboard/monitoring usage:
```bash
python run_load_tests.py -s all -u 100 -r 10 -t 300 --tags read
```

### 5. Individual Service Stress
Stress test a single service:
```bash
python run_load_tests.py -s metrics -u 100 -r 20 -t 300
```

## ⚠️ Warnings

### AI Chat Endpoints (Safe by Default)
The assistant service load tests use **MOCKED chat behavior** by default:
- Chat endpoints are tested with very short timeouts (infrastructure testing only)
- No actual AI API calls are made
- No costs are incurred
- Tests verify endpoint availability, request validation, and routing

The mock tests (`--tags mock-chat`) test:
- ✅ Endpoint accepts requests correctly
- ✅ Request validation works
- ✅ Provider routing/checking works
- ✅ Error handling for unconfigured providers
- ❌ Does NOT wait for actual AI responses
- ❌ Does NOT make billable API calls

Real AI testing code is commented out in the locustfile. To enable (⚠️ costs money!):
1. Uncomment the `AssistantRealChatUser` class in `locustfile_assistant.py`
2. Run with `--tags real-chat`

### Notification Endpoints
Some notification tests may send **real notifications** via email or Discord if those services are configured. Use the `--exclude-tags test-notify` flag to skip these.

### Safe Tags
All load tests are tagged with `safe` if they don't incur external costs:
```bash
# Run only safe tests (no AI costs, no real notifications)
locust -f locustfile_assistant.py --tags safe
```

### Speed Tests
Speed test endpoints take 30-60 seconds and consume bandwidth. They are excluded from regular load tests but can be triggered manually.

## Authentication Details

The load tests authenticate at startup using the provided credentials:
- `LOADTEST_USERNAME` / `LOADTEST_PASSWORD` - Used for all authenticated requests
- `LOADTEST_AUTH_HOST` - Base URL for auth login (default: `http://localhost:8002`)

If authentication fails:
1. Check that the user exists in your Cartographer instance
2. Verify the password is correct
3. Check the console for authentication error messages

The load tests will log successful authentication:
```
✅ Successfully authenticated as myuser
```

Or authentication failures:
```
❌ Authentication failed for myuser: 401
```

## Interpreting Results

### Key Metrics
- **RPS (Requests per Second)**: Throughput capacity
- **Response Time**: 50th, 95th, 99th percentiles
- **Failure Rate**: Percentage of failed requests
- **Active Users**: Concurrent user count during test

### Target Metrics (Example)
| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| p50 Response | < 100ms | < 500ms | > 1s |
| p95 Response | < 500ms | < 2s | > 5s |
| Failure Rate | < 0.1% | < 1% | > 5% |

## Integration with CI/CD

Example GitHub Actions workflow:

```yaml
- name: Run Load Tests
  run: |
    pip install -r load-tests/requirements.txt
    cd load-tests
    python run_load_tests.py -s all -u 20 -r 5 -t 60 --html load_test_report.html

- name: Upload Report
  uses: actions/upload-artifact@v3
  with:
    name: load-test-report
    path: load-tests/load_test_report.html
```

## Distributed Testing

For higher load, run Locust in distributed mode:

```bash
# Master node
locust -f locustfile_all.py --master --host=http://localhost:8000

# Worker nodes (run on multiple machines)
locust -f locustfile_all.py --worker --master-host=<master-ip>
```

## Customization

### Adding New Endpoints
1. Add a new `@task` decorated method to the appropriate User class
2. Set the task weight (frequency relative to other tasks)
3. Add appropriate tags

### Adjusting Load Patterns
Modify `wait_time` in User classes:
- `between(1, 3)` - Wait 1-3 seconds between requests
- `constant(2)` - Always wait 2 seconds
- `constant_pacing(5)` - Ensure each user makes a request every 5 seconds

### User Weights
Adjust `weight` attribute on User classes to change the ratio of different user types.
