#!/bin/bash

# Chronos MCP Run Script
# Uses uv for fast Python package management

# Set environment variables if not already set
export CALDAV_BASE_URL="${CALDAV_BASE_URL:-http://your-caldav-server:5232}"
export CALDAV_USERNAME="${CALDAV_USERNAME:-your-username}"
export CALDAV_PASSWORD="${CALDAV_PASSWORD:-your-password}"

# Change to script directory
cd "$(dirname "$0")"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed" >&2
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

# Sync dependencies (creates .venv if needed)
uv sync --quiet >&2

# Run the server with exec for proper signal handling
exec uv run python -m chronos_mcp.server
