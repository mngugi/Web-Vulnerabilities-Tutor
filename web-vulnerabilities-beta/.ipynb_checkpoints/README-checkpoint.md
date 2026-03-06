# Web Vulnerabilities Beta Project

## Overview
Web Vulnerabilities Beta is an AI tutor system for exploring web vulnerabilities using a local Ollama model and a SQLite database as the dataset source.

## Structure
web-vulnerabilities-beta/
- mcp_server/       MCP server exposing vulnerabilities as tools
- ai_agent/         AI tutor agent querying MCP and Ollama
- web/              Flask web UI
- data/             webvuln_dataset.db SQLite database
- requirements.txt  Python dependencies
- run.sh            Launch script

## Setup
1. Clone the project
2. Install dependencies: `pip install -r requirements.txt`
3. Launch: `chmod +x run.sh && ./run.sh`