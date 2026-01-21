#!/bin/bash
# generate-secrets.sh
# Generates secure secrets for Cartographer deployment
#
# Usage:
#   ./scripts/generate-secrets.sh          # Print to stdout
#   ./scripts/generate-secrets.sh > .env   # Write to .env file
#   ./scripts/generate-secrets.sh --append # Append to existing .env

set -e

# Colors for output (only if stdout is a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Check for openssl
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}Error: openssl is required but not installed.${NC}" >&2
    exit 1
fi

# Generate secrets
JWT_SECRET=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)

# Handle --append flag
if [ "$1" = "--append" ]; then
    if [ ! -f .env ]; then
        echo -e "${RED}Error: .env file not found. Create one first or run without --append.${NC}" >&2
        exit 1
    fi
    
    echo "" >> .env
    echo "# === Generated Secrets ($(date +%Y-%m-%d)) ===" >> .env
    echo "JWT_SECRET=${JWT_SECRET}" >> .env
    echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" >> .env
    echo "REDIS_PASSWORD=${REDIS_PASSWORD}" >> .env
    
    echo -e "${GREEN}Secrets appended to .env${NC}" >&2
    exit 0
fi

# Output secrets
cat << EOF
# ─────────────────────────────────────────────────────────────────────────────
# Cartographer Secrets - Generated $(date +%Y-%m-%d)
# ─────────────────────────────────────────────────────────────────────────────
# IMPORTANT: Keep these values secure and never commit to version control!

# JWT Secret - used for signing authentication tokens
# Must be the same across all services
JWT_SECRET=${JWT_SECRET}

# PostgreSQL password
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# Redis password (optional, uncomment if using authenticated Redis)
# REDIS_PASSWORD=${REDIS_PASSWORD}
EOF

# Print instructions to stderr (so they don't go into redirected output)
echo "" >&2
echo -e "${GREEN}Secrets generated successfully!${NC}" >&2
echo "" >&2
echo "To use these secrets:" >&2
echo "  1. Copy the output above to your .env file" >&2
echo "  2. Or run: $0 > .env" >&2
echo "  3. Or run: $0 --append (to add to existing .env)" >&2
