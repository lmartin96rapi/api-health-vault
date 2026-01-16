#!/bin/bash

# Script to create API key (wrapper for Python script)
# Usage: ./create_api_key.sh "API Key Name" "Description (optional)"

NAME="${1:-}"
DESCRIPTION="${2:-}"

if [ -z "$NAME" ]; then
    echo "Usage: ./create_api_key.sh \"API Key Name\" [\"Description\"]"
    echo ""
    echo "Examples:"
    echo "  ./create_api_key.sh \"Backend Service\""
    echo "  ./create_api_key.sh \"Backend Service\" \"API key for backend integration\""
    exit 1
fi

# Check if running in Docker or locally
if [ -f /.dockerenv ] || [ -n "${DOCKER_CONTAINER:-}" ]; then
    # Running inside Docker
    python scripts/create_api_key.py --name "$NAME" ${DESCRIPTION:+--description "$DESCRIPTION"}
else
    # Try to run in Docker container if available
    if docker ps --format '{{.Names}}' | grep -q "api_health_insurance-api"; then
        echo "Running in Docker container..."
        docker exec api_health_insurance-api-1 python scripts/create_api_key.py --name "$NAME" ${DESCRIPTION:+--description "$DESCRIPTION"}
    else
        # Run locally
        python3 scripts/create_api_key.py --name "$NAME" ${DESCRIPTION:+--description "$DESCRIPTION"}
    fi
fi

