#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Cartographer Deployment Script
# ─────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  build       Build all Docker images locally"
    echo "  push        Push images to registry (requires REGISTRY env var)"
    echo "  up          Start all services with docker-compose"
    echo "  down        Stop all services"
    echo "  logs        View logs from all services"
    echo "  restart     Restart all services"
    echo "  status      Show status of services"
    echo ""
    echo "Options:"
    echo "  --prod      Use production compose file (pre-built images)"
    echo "  --tag TAG   Image tag to use (default: latest)"
    echo ""
    echo "Environment Variables:"
    echo "  REGISTRY    Container registry prefix (e.g., ghcr.io/username)"
    echo "  TAG         Image tag (default: latest)"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 up"
    echo "  REGISTRY=myuser TAG=v1.0.0 $0 push"
    echo "  REGISTRY=myuser $0 up --prod"
}

# Parse arguments
COMMAND=""
USE_PROD=false
TAG="${TAG:-latest}"

while [[ $# -gt 0 ]]; do
    case $1 in
        build|push|up|down|logs|restart|status)
            COMMAND=$1
            shift
            ;;
        --prod)
            USE_PROD=true
            shift
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

if [ -z "$COMMAND" ]; then
    usage
    exit 1
fi

# Select compose file
if [ "$USE_PROD" = true ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

case $COMMAND in
    build)
        echo -e "${GREEN}Building Docker images...${NC}"
        echo "Building cartographer-app..."
        docker build -t cartographer-app:$TAG .
        echo "Building cartographer-health..."
        docker build -t cartographer-health:$TAG ./health-service
        echo -e "${GREEN}✓ Build complete${NC}"
        ;;
    
    push)
        if [ -z "$REGISTRY" ]; then
            echo -e "${RED}Error: REGISTRY environment variable is required${NC}"
            echo "Example: REGISTRY=ghcr.io/username $0 push"
            exit 1
        fi
        echo -e "${GREEN}Pushing images to $REGISTRY...${NC}"
        
        # Tag and push app
        docker tag cartographer-app:$TAG $REGISTRY/cartographer-app:$TAG
        docker push $REGISTRY/cartographer-app:$TAG
        
        # Tag and push health service
        docker tag cartographer-health:$TAG $REGISTRY/cartographer-health:$TAG
        docker push $REGISTRY/cartographer-health:$TAG
        
        echo -e "${GREEN}✓ Push complete${NC}"
        ;;
    
    up)
        echo -e "${GREEN}Starting services with $COMPOSE_FILE...${NC}"
        if [ "$USE_PROD" = true ]; then
            REGISTRY=$REGISTRY TAG=$TAG docker-compose -f $COMPOSE_FILE up -d
        else
            docker-compose -f $COMPOSE_FILE up --build -d
        fi
        echo ""
        echo -e "${GREEN}✓ Services started${NC}"
        echo ""
        echo "Access the application:"
        echo "  Main App:        http://localhost:8000"
        echo "  Health Service:  http://localhost:8001"
        ;;
    
    down)
        echo -e "${YELLOW}Stopping services...${NC}"
        docker-compose -f $COMPOSE_FILE down
        echo -e "${GREEN}✓ Services stopped${NC}"
        ;;
    
    logs)
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    
    restart)
        echo -e "${YELLOW}Restarting services...${NC}"
        docker-compose -f $COMPOSE_FILE restart
        echo -e "${GREEN}✓ Services restarted${NC}"
        ;;
    
    status)
        echo -e "${GREEN}Service Status:${NC}"
        docker-compose -f $COMPOSE_FILE ps
        ;;
    
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        usage
        exit 1
        ;;
esac

