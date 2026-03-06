"""
server.py
---------
WebVuln-AI MCP Server

Implements the Model Context Protocol (MCP) to expose web vulnerability
data as callable tools. The server communicates over stdio (default) or
TCP and is consumed by the AI tutor agent.

Protocol: JSON-RPC 2.0 over newline-delimited messages.

Supported MCP methods:
  - initialize
  - tools/list
  - tools/call
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import logging
from typing import Any

# Add project root to path so imports work when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import dispatch, get_tool_schemas
from vuln_loader import load_vulnerabilities

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MCP] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
log = logging.getLogger("mcp_server")

# ── Config ─────────────────────────────────────────────────────────────────────
SERVER_NAME = "webvuln-ai-mcp"
SERVER_VERSION = "1.0.0"
HOST = os.getenv("MCP_SERVER_HOST", "localhost")
PORT = int(os.getenv("MCP_SERVER_PORT", "8765"))
TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")  # "stdio" or "tcp"


# ── JSON-RPC helpers ───────────────────────────────────────────────────────────
def _ok(request_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ── Request dispatcher ─────────────────────────────────────────────────────────
async def handle_request(message: dict) -> dict | None:
    """
    Route a JSON-RPC request to the correct MCP handler.
    Returns None for notifications (no id field).
    """
    method = message.get("method", "")
    req_id = message.get("id")
    params = message.get("params", {})

    # Notifications — no response needed
    if req_id is None and method.startswith("notifications/"):
        return None

    log.info(f"← {method}  id={req_id}")

    # ── initialize ─────────────────────────────────────────────────────────────
    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })

    # ── tools/list ─────────────────────────────────────────────────────────────
    if method == "tools/list":
        schemas = get_tool_schemas()
        # Convert to MCP-compatible format
        tools_payload = []
        for s in schemas:
            tools_payload.append({
                "name": s["name"],
                "description": s["description"],
                "inputSchema": s.get("input_schema", {"type": "object", "properties": {}}),
            })
        return _ok(req_id, {"tools": tools_payload})

    # ── tools/call ─────────────────────────────────────────────────────────────
    if method == "tools/call":
        tool_name = params.get("name")
        tool_input = params.get("arguments", {})

        if not tool_name:
            return _err(req_id, -32602, "Missing 'name' in tools/call params")

        log.info(f"  ↳ calling tool '{tool_name}' with {list(tool_input.keys())}")
        result = dispatch(tool_name, tool_input)

        if "error" in result:
            return _ok(req_id, {
                "content": [{"type": "text", "text": result["error"]}],
                "isError": True,
            })

        return _ok(req_id, {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": False,
        })

    # ── ping ───────────────────────────────────────────────────────────────────
    if method == "ping":
        return _ok(req_id, {})

    # ── unknown ────────────────────────────────────────────────────────────────
    return _err(req_id, -32601, f"Method not found: '{method}'")


# ── stdio transport ────────────────────────────────────────────────────────────
async def run_stdio():
    """Run the MCP server over stdin/stdout (default for local tool use)."""
    log.info(f"MCP server '{SERVER_NAME}' v{SERVER_VERSION} running on stdio")
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    loop = asyncio.get_event_loop()

    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    write_transport, _ = await loop.connect_write_pipe(
        asyncio.BaseProtocol, sys.stdout.buffer
    )

    async def send(msg: dict):
        line = json.dumps(msg, ensure_ascii=False) + "\n"
        write_transport.write(line.encode("utf-8"))

    while True:
        try:
            line = await reader.readline()
            if not line:
                break
            message = json.loads(line.decode("utf-8").strip())
            response = await handle_request(message)
            if response is not None:
                await send(response)
        except json.JSONDecodeError as e:
            log.error(f"JSON parse error: {e}")
        except Exception as e:
            log.exception(f"Unhandled error: {e}")
            break


# ── TCP transport ──────────────────────────────────────────────────────────────
async def handle_tcp_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    log.info(f"New TCP connection from {addr}")

    async def send(msg: dict):
        line = json.dumps(msg, ensure_ascii=False) + "\n"
        writer.write(line.encode("utf-8"))
        await writer.drain()

    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                message = json.loads(line.decode("utf-8").strip())
                response = await handle_request(message)
                if response is not None:
                    await send(response)
            except json.JSONDecodeError as e:
                log.warning(f"JSON decode error from {addr}: {e}")
    except asyncio.IncompleteReadError:
        pass
    finally:
        writer.close()
        log.info(f"Connection from {addr} closed")


async def run_tcp():
    """Run the MCP server as a TCP server."""
    log.info(f"MCP server '{SERVER_NAME}' v{SERVER_VERSION} listening on {HOST}:{PORT}")
    server = await asyncio.start_server(handle_tcp_client, HOST, PORT)
    async with server:
        await server.serve_forever()


# ── Entry point ────────────────────────────────────────────────────────────────
async def main():
    # Pre-load dataset at startup so first tool call is fast
    log.info("Pre-loading vulnerability dataset...")
    db = load_vulnerabilities()
    log.info(f"Dataset ready: {len(db)} vulnerabilities loaded.")

    if TRANSPORT == "tcp":
        await run_tcp()
    else:
        await run_stdio()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("MCP server stopped.")