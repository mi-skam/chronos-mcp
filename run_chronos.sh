#!/bin/bash

# Chronos MCP Run Script

# Set environment variables if not already set
export CALDAV_BASE_URL="${CALDAV_BASE_URL:-http://your-caldav-server:5232}"
export CALDAV_USERNAME="${CALDAV_USERNAME:-your-username}"
export CALDAV_PASSWORD="${CALDAV_PASSWORD:-your-password}"

# Change to script directory
cd "$(dirname "$0")"

# Create virtual environment if needed  
if [ ! -d "venv" ]; then
    python3 -m venv venv >&2
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies quietly, all output to stderr
pip install -e . -q >&2 2>&1

# Run the server with exec for proper signal handling
exec python -m chronos_mcp.server
