#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Cartographer Development Script
# Platform-agnostic script to run all services locally with hot reload
# ─────────────────────────────────────────────────────────────────────────────
#
# Usage:
#   ./dev.sh              # Start all services
#   ./dev.sh start        # Start all services
#   ./dev.sh stop         # Stop all services
#   ./dev.sh status       # Check service status
#   ./dev.sh logs [svc]   # Tail logs for a service
#   ./dev.sh setup        # Install dependencies
#   ./dev.sh db           # Start only database services (postgres, redis)
#   ./dev.sh [service]    # Start specific service(s): backend, frontend, auth, etc.
#
# Services:
#   backend     - Main API gateway (port 8000)
#   frontend    - Vue.js frontend (port 5173)
#   auth        - Authentication service (port 8002)
#   health      - Health check service (port 8001)
#   metrics     - Metrics service (port 8003)
#   assistant   - AI assistant service (port 8004)
#   notification - Notification service (port 8005)
#   postgres    - PostgreSQL database (port 5432)
#   redis       - Redis cache (port 6379)
#
# ─────────────────────────────────────────────────────────────────────────────

set -e

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Service ports (Bash 3.x compatible)
get_port() {
    case "$1" in
        backend) echo 8000 ;;
        health) echo 8001 ;;
        auth) echo 8002 ;;
        metrics) echo 8003 ;;
        assistant) echo 8004 ;;
        notification) echo 8005 ;;
        frontend) echo 5173 ;;
        postgres) echo 5432 ;;
        redis) echo 6379 ;;
        *) echo "" ;;
    esac
}

# Service directories
get_service_dir() {
    case "$1" in
        backend) echo "backend" ;;
        health) echo "health-service" ;;
        auth) echo "auth-service" ;;
        metrics) echo "metrics-service" ;;
        assistant) echo "assistant-service" ;;
        notification) echo "notification-service" ;;
        frontend) echo "frontend" ;;
        *) echo "" ;;
    esac
}

# Service colors for output
get_color() {
    case "$1" in
        backend) echo "$BLUE" ;;
        health) echo "$GREEN" ;;
        auth) echo "$MAGENTA" ;;
        metrics) echo "$CYAN" ;;
        assistant) echo "$YELLOW" ;;
        notification) echo "$RED" ;;
        frontend) echo "$WHITE" ;;
        postgres) echo "$GREEN" ;;
        redis) echo "$RED" ;;
        *) echo "$WHITE" ;;
    esac
}

# Python services (need venv)
PYTHON_SERVICES="backend health auth metrics assistant notification"

# All services in start order
ALL_SERVICES="postgres redis health auth metrics assistant notification backend frontend"

# Log directory
LOG_DIR="$SCRIPT_DIR/.dev-logs"
PID_DIR="$SCRIPT_DIR/.dev-pids"

# ═══════════════════════════════════════════════════════════════════════════════
# Colors and Output
# ═══════════════════════════════════════════════════════════════════════════════

# Check if terminal supports colors
if [[ -t 1 ]] && command -v tput &>/dev/null && [[ $(tput colors 2>/dev/null) -ge 8 ]]; then
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    MAGENTA=$(tput setaf 5)
    CYAN=$(tput setaf 6)
    WHITE=$(tput setaf 7)
    BOLD=$(tput bold)
    RESET=$(tput sgr0)
else
    RED="" GREEN="" YELLOW="" BLUE="" MAGENTA="" CYAN="" WHITE="" BOLD="" RESET=""
fi

log() { echo -e "${BOLD}[dev]${RESET} $*"; }
log_service() { 
    local svc="$1"
    shift
    local color=$(get_color "$svc")
    echo -e "${color}${BOLD}[$svc]${RESET} $*"
}
error() { echo -e "${RED}${BOLD}[error]${RESET} $*" >&2; }
success() { echo -e "${GREEN}${BOLD}[✓]${RESET} $*"; }
warn() { echo -e "${YELLOW}${BOLD}[!]${RESET} $*"; }

# ═══════════════════════════════════════════════════════════════════════════════
# Platform Detection
# ═══════════════════════════════════════════════════════════════════════════════

detect_platform() {
    case "$(uname -s)" in
        Darwin*) PLATFORM="macos" ;;
        Linux*)  PLATFORM="linux" ;;
        MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
        *)       PLATFORM="unknown" ;;
    esac
    
    # Check for WSL
    if [[ -f /proc/version ]] && grep -qi microsoft /proc/version 2>/dev/null; then
        PLATFORM="wsl"
    fi
    
    log "Platform: $PLATFORM"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Dependency Checks
# ═══════════════════════════════════════════════════════════════════════════════

check_dependencies() {
    local missing=""
    local python_cmd="${PYTHON_CMD:-python3}"
    
    # Python 3.10+
    if ! command -v "$python_cmd" &>/dev/null; then
        missing="$missing python3"
    else
        local py_version=$("$python_cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        local py_major="${py_version%.*}"
        local py_minor="${py_version#*.}"
        local py_platform=$("$python_cmd" -c 'import sys; print(sys.platform)')
        
        log "Python: $py_version ($python_cmd)"
        
        if [[ "$py_major" -lt 3 ]] || { [[ "$py_major" -eq 3 ]] && [[ "$py_minor" -lt 10 ]]; }; then
            error "Python 3.10+ required, found $py_version"
            exit 1
        fi
        
        # Detect MSYS2 Python on Windows - incompatible with native extensions
        if [[ "$PLATFORM" == "windows" ]] && command -v "$python_cmd" &>/dev/null; then
            local py_path=$(command -v "$python_cmd")
            if [[ "$py_path" == *"/msys64/"* ]] || [[ "$py_path" == *"/ucrt64/"* ]] || [[ "$py_path" == *"/mingw64/"* ]]; then
                error "MSYS2 Python detected - incompatible with native extensions (asyncpg, pydantic-core)!"
                echo ""
                echo "Please install official Windows Python from https://www.python.org/downloads/"
                echo "Recommended: Python 3.11 or 3.12"
                echo ""
                echo "After installing, either:"
                echo "  1. Add Windows Python to PATH before MSYS2"
                echo "  2. Use: export PYTHON_CMD=/c/Users/YourName/AppData/Local/Programs/Python/Python312/python.exe"
                echo "  3. Use WSL2 for a better development experience: wsl --install"
                echo ""
                exit 1
            fi
        fi
        
        # Warn about Python 3.13 compatibility issues
        if [[ "$py_major" -eq 3 ]] && [[ "$py_minor" -ge 13 ]]; then
            warn "Python 3.13 detected. Some packages (asyncpg) may not have pre-built wheels yet."
            warn "If you encounter build errors, consider using Python 3.11 or 3.12."
            warn "To use a different Python: export PYTHON_CMD=/path/to/python3.11"
            echo ""
        fi
    fi
    
    # Node.js
    if ! command -v node &>/dev/null; then
        missing="$missing node"
    fi
    
    # npm or bun
    if ! command -v npm &>/dev/null && ! command -v bun &>/dev/null; then
        missing="$missing npm"
    fi
    
    # Docker (optional but needed for postgres/redis)
    if ! command -v docker &>/dev/null; then
        warn "Docker not found - postgres/redis must be running separately"
        HAS_DOCKER=false
    else
        HAS_DOCKER=true
    fi
    
    if [[ -n "$missing" ]]; then
        error "Missing dependencies:$missing"
        error "Please install them and try again."
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Environment Setup
# ═══════════════════════════════════════════════════════════════════════════════

load_env() {
    # Load .env file if it exists
    if [[ -f "$SCRIPT_DIR/.env" ]]; then
        log "Loading .env file"
        set -a
        # shellcheck disable=SC1091
        source "$SCRIPT_DIR/.env"
        set +a
    elif [[ -f "$SCRIPT_DIR/.example.env" ]]; then
        warn "No .env file found. Copy .example.env to .env and configure it."
        warn "Using defaults for development..."
    fi
    
    # Set defaults for development
    export POSTGRES_USER="${POSTGRES_USER:-cartographer}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-cartographer_secret}"
    export POSTGRES_DB="${POSTGRES_DB:-cartographer}"
    export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5432/$POSTGRES_DB}"
    export JWT_SECRET="${JWT_SECRET:-cartographer-dev-secret-change-in-production}"
    export CORS_ORIGINS="${CORS_ORIGINS:-*}"
    export APPLICATION_URL="${APPLICATION_URL:-http://localhost:5173}"
    
    # Service URLs
    export HEALTH_SERVICE_URL="${HEALTH_SERVICE_URL:-http://localhost:8001}"
    export AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://localhost:8002}"
    export METRICS_SERVICE_URL="${METRICS_SERVICE_URL:-http://localhost:8003}"
    export ASSISTANT_SERVICE_URL="${ASSISTANT_SERVICE_URL:-http://localhost:8004}"
    export NOTIFICATION_SERVICE_URL="${NOTIFICATION_SERVICE_URL:-http://localhost:8005}"
    export BACKEND_SERVICE_URL="${BACKEND_SERVICE_URL:-http://localhost:8000}"
    export REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Virtual Environment Management
# ═══════════════════════════════════════════════════════════════════════════════

ensure_venv() {
    local service=$1
    local service_dir=$(get_service_dir "$service")
    local venv_dir="$SCRIPT_DIR/$service_dir/.venv"
    local python_cmd="${PYTHON_CMD:-python3}"
    
    if [[ ! -d "$venv_dir" ]]; then
        log_service "$service" "Creating virtual environment..."
        "$python_cmd" -m venv "$venv_dir"
    fi
    
    # Activate venv - handle Windows vs Unix paths
    # shellcheck disable=SC1091
    if [[ "$PLATFORM" == "windows" && -f "$venv_dir/Scripts/activate" ]]; then
        source "$venv_dir/Scripts/activate"
    else
        source "$venv_dir/bin/activate"
    fi
    
    # Check if requirements are installed
    local req_file="$SCRIPT_DIR/$service_dir/requirements.txt"
    local marker_file="$venv_dir/.requirements-installed"
    
    if [[ ! -f "$marker_file" ]] || [[ "$req_file" -nt "$marker_file" ]]; then
        log_service "$service" "Installing dependencies..."
        # Use python -m pip instead of pip directly to avoid Windows file locking issues
        python -m pip install -q --upgrade pip 2>/dev/null || true
        python -m pip install -q -r "$req_file"
        touch "$marker_file"
    fi
}

setup_frontend() {
    local frontend_dir="$SCRIPT_DIR/frontend"
    
    if [[ ! -d "$frontend_dir/node_modules" ]]; then
        log_service "frontend" "Installing dependencies..."
        cd "$frontend_dir"
        if command -v bun &>/dev/null; then
            bun install
        else
            npm install
        fi
        cd "$SCRIPT_DIR"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Service Management
# ═══════════════════════════════════════════════════════════════════════════════

is_port_in_use() {
    local port=$1
    if command -v lsof &>/dev/null; then
        lsof -i ":$port" &>/dev/null
    elif command -v ss &>/dev/null; then
        ss -tuln | grep -q ":$port "
    elif command -v netstat &>/dev/null; then
        # Windows uses different netstat syntax
        if [[ "$PLATFORM" == "windows" ]]; then
            netstat -ano | grep -q ":$port "
        else
            netstat -tuln | grep -q ":$port "
        fi
    else
        return 1
    fi
}

wait_for_port() {
    local port=$1
    local service=$2
    local timeout=${3:-30}
    local count=0
    
    log_service "$service" "Waiting for port $port..."
    while ! is_port_in_use "$port"; do
        sleep 1
        count=$((count + 1))
        if [[ $count -ge $timeout ]]; then
            error "$service failed to start (timeout waiting for port $port)"
            return 1
        fi
    done
    success "$service is running on port $port"
}

start_postgres() {
    local port=$(get_port postgres)
    
    if is_port_in_use "$port"; then
        success "PostgreSQL already running on port $port"
        return 0
    fi
    
    if [[ "$HAS_DOCKER" != "true" ]]; then
        error "Docker not available - please start PostgreSQL manually on port $port"
        return 1
    fi
    
    log_service "postgres" "Starting PostgreSQL..."
    docker run -d --rm \
        --name cartographer-postgres-dev \
        -p 5432:5432 \
        -e POSTGRES_USER="$POSTGRES_USER" \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -e POSTGRES_DB="$POSTGRES_DB" \
        -v cartographer-postgres-dev:/var/lib/postgresql/data \
        postgres:16-alpine \
        >/dev/null
    
    wait_for_port "$port" "postgres" 30
}

start_redis() {
    local port=$(get_port redis)
    
    if is_port_in_use "$port"; then
        success "Redis already running on port $port"
        return 0
    fi
    
    if [[ "$HAS_DOCKER" != "true" ]]; then
        error "Docker not available - please start Redis manually on port $port"
        return 1
    fi
    
    log_service "redis" "Starting Redis..."
    docker run -d --rm \
        --name cartographer-redis-dev \
        -p 6379:6379 \
        -v cartographer-redis-dev:/data \
        redis:7-alpine \
        >/dev/null
    
    wait_for_port "$port" "redis" 15
}

start_python_service() {
    local service=$1
    local port=$(get_port "$service")
    local service_dir=$(get_service_dir "$service")
    
    if is_port_in_use "$port"; then
        warn "$service already running on port $port"
        return 0
    fi
    
    mkdir -p "$LOG_DIR" "$PID_DIR"
    
    ensure_venv "$service"
    
    log_service "$service" "Starting on port $port with hot reload..."
    
    # Start uvicorn with reload
    cd "$SCRIPT_DIR/$service_dir"
    
    # Use unbuffered output and redirect to log file
    PYTHONUNBUFFERED=1 \
    python -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port "$port" \
        --reload \
        --reload-dir app \
        > "$LOG_DIR/$service.log" 2>&1 &
    
    local pid=$!
    echo "$pid" > "$PID_DIR/$service.pid"
    
    cd "$SCRIPT_DIR"
    deactivate 2>/dev/null || true
    
    wait_for_port "$port" "$service" 30
}

start_frontend() {
    local port=$(get_port frontend)
    
    if is_port_in_use "$port"; then
        warn "Frontend already running on port $port"
        return 0
    fi
    
    mkdir -p "$LOG_DIR" "$PID_DIR"
    
    setup_frontend
    
    log_service "frontend" "Starting Vite dev server on port $port..."
    
    cd "$SCRIPT_DIR/frontend"
    
    if command -v bun &>/dev/null; then
        bun run dev > "$LOG_DIR/frontend.log" 2>&1 &
    else
        npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    fi
    
    local pid=$!
    echo "$pid" > "$PID_DIR/frontend.pid"
    
    cd "$SCRIPT_DIR"
    
    wait_for_port "$port" "frontend" 30
}

stop_service() {
    local service=$1
    local pid_file="$PID_DIR/$service.pid"
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_service "$service" "Stopping (PID $pid)..."
            kill "$pid" 2>/dev/null || true
            # Wait for graceful shutdown
            local count=0
            while kill -0 "$pid" 2>/dev/null && [[ $count -lt 10 ]]; do
                sleep 0.5
                count=$((count + 1))
            done
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$pid_file"
    fi
}

stop_docker_service() {
    local container=$1
    if docker ps -q -f name="$container" 2>/dev/null | grep -q .; then
        log "Stopping $container..."
        docker stop "$container" >/dev/null 2>&1 || true
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════════════════════════════════

cmd_setup() {
    log "Setting up development environment..."
    
    check_dependencies
    load_env
    
    # Setup Python services
    for service in $PYTHON_SERVICES; do
        ensure_venv "$service"
        deactivate 2>/dev/null || true
    done
    
    # Setup frontend
    setup_frontend
    
    success "Development environment ready!"
    echo ""
    echo "Next steps:"
    echo "  1. Copy .example.env to .env and configure your settings"
    echo "  2. Run ./dev.sh to start all services"
}

cmd_start() {
    local services="$*"
    
    check_dependencies
    load_env
    
    # If no services specified, start all
    if [[ -z "$services" ]]; then
        services="$ALL_SERVICES"
    fi
    
    log "Starting services: $services"
    echo ""
    
    for service in $services; do
        case "$service" in
            postgres) start_postgres ;;
            redis) start_redis ;;
            frontend) start_frontend ;;
            backend|health|auth|metrics|assistant|notification)
                start_python_service "$service"
                ;;
            db)
                start_postgres
                start_redis
                ;;
            *)
                error "Unknown service: $service"
                ;;
        esac
    done
    
    echo ""
    success "All services started!"
    echo ""
    echo "Service URLs:"
    echo "  ${CYAN}Frontend:${RESET}     http://localhost:$(get_port frontend)"
    echo "  ${BLUE}Backend:${RESET}      http://localhost:$(get_port backend)"
    echo "  ${MAGENTA}Auth:${RESET}         http://localhost:$(get_port auth)"
    echo "  ${GREEN}Health:${RESET}       http://localhost:$(get_port health)"
    echo "  ${CYAN}Metrics:${RESET}      http://localhost:$(get_port metrics)"
    echo "  ${YELLOW}Assistant:${RESET}    http://localhost:$(get_port assistant)"
    echo "  ${RED}Notification:${RESET} http://localhost:$(get_port notification)"
    echo ""
    echo "Logs: $LOG_DIR/"
    echo "Press Ctrl+C to stop all services"
    echo ""
    
    # Tail all logs
    if [[ -d "$LOG_DIR" ]] && ls "$LOG_DIR"/*.log 1>/dev/null 2>&1; then
        tail -f "$LOG_DIR"/*.log 2>/dev/null &
        TAIL_PID=$!
    fi
    
    # Wait for interrupt
    trap 'cmd_stop; exit 0' INT TERM
    wait
}

cmd_stop() {
    log "Stopping all services..."
    
    # Stop Python services and frontend
    for service in $PYTHON_SERVICES frontend; do
        stop_service "$service"
    done
    
    # Stop Docker containers
    if [[ "$HAS_DOCKER" == "true" ]]; then
        stop_docker_service "cartographer-postgres-dev"
        stop_docker_service "cartographer-redis-dev"
    fi
    
    # Kill tail process if running
    if [[ -n "${TAIL_PID:-}" ]]; then
        kill "$TAIL_PID" 2>/dev/null || true
    fi
    
    success "All services stopped"
}

cmd_status() {
    echo ""
    echo "${BOLD}Service Status${RESET}"
    echo "─────────────────────────────────────"
    
    for service in postgres redis backend frontend health auth metrics assistant notification; do
        local port=$(get_port "$service")
        local color=$(get_color "$service")
        
        if is_port_in_use "$port"; then
            echo -e "${color}${BOLD}$service${RESET}: ${GREEN}Running${RESET} (port $port)"
        else
            echo -e "${color}${BOLD}$service${RESET}: ${RED}Stopped${RESET}"
        fi
    done
    echo ""
}

cmd_logs() {
    local service=${1:-all}
    
    if [[ "$service" == "all" ]]; then
        if [[ -d "$LOG_DIR" ]]; then
            tail -f "$LOG_DIR"/*.log
        else
            error "No logs found"
        fi
    else
        local log_file="$LOG_DIR/$service.log"
        if [[ -f "$log_file" ]]; then
            tail -f "$log_file"
        else
            error "No logs found for $service"
        fi
    fi
}

cmd_help() {
    cat << 'EOF'
Cartographer Development Script

Usage:
  ./dev.sh [command] [services...]

Commands:
  start [services...]  Start services (default: all)
  stop                 Stop all services
  status               Show service status
  logs [service]       Tail logs (default: all)
  setup                Install dependencies
  db                   Start only database services
  help                 Show this help

Services:
  backend              Main API gateway (port 8000)
  frontend             Vue.js frontend (port 5173)
  auth                 Authentication service (port 8002)
  health               Health check service (port 8001)
  metrics              Metrics service (port 8003)
  assistant            AI assistant service (port 8004)
  notification         Notification service (port 8005)
  postgres             PostgreSQL database (port 5432)
  redis                Redis cache (port 6379)

Examples:
  ./dev.sh                    # Start all services
  ./dev.sh backend frontend   # Start only backend and frontend
  ./dev.sh db                 # Start only postgres and redis
  ./dev.sh status             # Check what's running
  ./dev.sh logs backend       # Tail backend logs
  ./dev.sh stop               # Stop everything

Environment:
  Copy .example.env to .env and configure your settings before running.

EOF
}

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

main() {
    detect_platform
    
    local cmd="${1:-start}"
    shift || true
    
    case "$cmd" in
        start|"")   cmd_start "$@" ;;
        stop)       cmd_stop ;;
        status)     cmd_status ;;
        logs)       cmd_logs "$@" ;;
        setup)      cmd_setup ;;
        db)         
            check_dependencies
            load_env
            start_postgres
            start_redis
            ;;
        help|-h|--help) cmd_help ;;
        # Single service shortcuts
        backend|frontend|health|auth|metrics|assistant|notification)
            cmd_start "$cmd" "$@"
            ;;
        *)
            error "Unknown command: $cmd"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
