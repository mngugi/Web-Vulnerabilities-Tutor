#!/bin/bash
# Start MCP server
python mcp_server/server.py &

# Start Flask web app
python web/app.py