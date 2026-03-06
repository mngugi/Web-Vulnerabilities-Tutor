#!/bin/bash

# Navigate to the project root (where run.sh lives)
cd "$(dirname "$0")"

# 1️⃣ Start MCP server in background using -m
echo "Starting MCP server..."
python -m mcp_server.server &

# 2️⃣ Start Flask web app using -m
echo "Starting Flask web app..."
python -m web.app