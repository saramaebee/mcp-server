#!/bin/bash

# MCP Server with Python Watchdog File Watching
# Usage: ./run-mcp-watchdog.sh [mcp-args...]

set -e

SERVER_DIR="/Users/sara/work/fossa/devrev/mcp-server"
cd "$SERVER_DIR"

echo "🔄 Starting MCP Server with Python watchdog (no fswatch needed)..."
echo ""

# Run the Python wrapper that handles file watching and server management
exec /Users/sara/.local/bin/uv run python mcp_wrapper.py "$@"