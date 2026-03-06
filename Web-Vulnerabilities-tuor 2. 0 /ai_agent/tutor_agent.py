"""
tutor_agent.py
--------------
WebVuln-AI Tutor Agent — powered by Ollama (100% local, no API key needed)

Uses Ollama's OpenAI-compatible API with function calling to answer
questions about web vulnerabilities from the WebVuln-Plus dataset.

Ollama runs locally on http://localhost:11434

Two modes:
  - CLI mode:     python tutor_agent.py
  - Library mode: get_response(user_message, history) called from Flask

Setup:
  1. Install Ollama:  curl -fsSL https://ollama.com/install.sh | sh
  2. Pull a model:    ollama pull llama3.2
  3. Run this agent:  python tutor_agent.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Generator

import requests

# ── Path setup ─────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp_server"))

from tools import dispatch, get_tool_schemas

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AGENT] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
log = logging.getLogger("tutor_agent")

# ── Config ─────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL           = os.getenv("OLLAMA_MODEL", "llama3.2")   # change to llama3.1:8b etc
MAX_TOKENS      = 2048
MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = """You are WebVuln-AI, an expert cybersecurity tutor specialising in web application vulnerabilities.

You have access to a structured database of 100+ web vulnerabilities from the WebVuln-Plus project, covering OWASP Top 10 and beyond. Always use your tools to fetch accurate data before answering.

Your teaching style:
- Clear and educational — explain concepts at the right level for the student
- Practical — include real examples, PoC scenarios, and tool recommendations  
- Structured — use headings, bullet points, and code blocks where helpful
- Safe — always note that PoC payloads are for educational/research purposes only

When a user asks about a vulnerability:
1. Call get_vulnerability or search_vulnerabilities to fetch the data first
2. Explain the concept in plain language
3. Show a concrete example of how it works
4. Explain how to detect and mitigate it
5. Suggest testing tools

For quizzes use get_quiz_question. For broad questions use list_vulnerabilities or get_by_category.

Always be accurate. Never fabricate vulnerability details."""


# ── Build Ollama tool schemas ──────────────────────────────────────────────────
def _build_ollama_tools() -> list[dict]:
    """Convert MCP tool schemas to Ollama/OpenAI function-calling format."""
    tools = []
    for schema in get_tool_schemas():
        tools.append({
            "type": "function",
            "function": {
                "name":        schema["name"],
                "description": schema["description"],
                "parameters":  schema.get("input_schema", {
                    "type":       "object",
                    "properties": {},
                }),
            },
        })
    return tools


# ── Tool execution ─────────────────────────────────────────────────────────────
def _run_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return result as JSON string."""
    log.info(f"Running tool: {tool_name}({list(tool_input.keys())})")
    result = dispatch(tool_name, tool_input)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Ollama API call ────────────────────────────────────────────────────────────
def _ollama_chat(messages: list[dict], tools: list[dict], stream: bool = False):
    """
    Call the Ollama /api/chat endpoint.
    Returns the parsed JSON response or a streaming response object.
    """
    url     = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model":    MODEL,
        "messages": messages,
        "tools":    tools,
        "stream":   stream,
        "options":  {"num_predict": MAX_TOKENS},
    }

    try:
        response = requests.post(url, json=payload, stream=stream, timeout=120)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot connect to Ollama at {OLLAMA_BASE_URL}.\n"
            "Make sure Ollama is running: ollama serve"
        )

    if stream:
        return response
    return response.json()


# ── Core agent loop ────────────────────────────────────────────────────────────
def get_response(
    user_message: str,
    history: list[dict] | None = None,
) -> str:
    """
    Send a message to the tutor agent and return the full response string.
    Handles multi-round tool use automatically.
    """
    tools    = _build_ollama_tools()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += list(history or [])
    messages.append({"role": "user", "content": user_message})

    for round_num in range(MAX_TOOL_ROUNDS):
        log.info(f"Agent loop round {round_num + 1}/{MAX_TOOL_ROUNDS}")

        data          = _ollama_chat(messages, tools, stream=False)
        message       = data.get("message", {})
        finish_reason = "tool_calls" if message.get("tool_calls") else "stop"

        log.info(f"Finish reason: {finish_reason}")

        # ── Tool calls ─────────────────────────────────────────────────────────
        if finish_reason == "tool_calls":
            messages.append(message)

            for tc in message.get("tool_calls", []):
                fn        = tc.get("function", {})
                tool_name = fn.get("name", "")
                try:
                    tool_input = fn.get("arguments", {})
                    if isinstance(tool_input, str):
                        tool_input = json.loads(tool_input)
                except (json.JSONDecodeError, TypeError):
                    tool_input = {}

                result = _run_tool(tool_name, tool_input)
                messages.append({
                    "role":    "tool",
                    "content": result,
                })
            continue

        # ── Final answer ───────────────────────────────────────────────────────
        return message.get("content", "")

    return "I'm sorry, I wasn't able to complete the response. Please try again."


# ── Streaming response ─────────────────────────────────────────────────────────
def get_response_streaming(
    user_message: str,
    history: list[dict] | None = None,
) -> Generator[str, None, None]:
    """
    Streaming version — resolves tool calls first, then streams final answer
    token by token from Ollama.
    """
    tools    = _build_ollama_tools()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += list(history or [])
    messages.append({"role": "user", "content": user_message})

    for round_num in range(MAX_TOOL_ROUNDS):
        log.info(f"Streaming round {round_num + 1}/{MAX_TOOL_ROUNDS}")

        # Non-streaming pass first to detect tool calls
        data          = _ollama_chat(messages, tools, stream=False)
        message       = data.get("message", {})
        has_tool_call = bool(message.get("tool_calls"))

        # ── Tool calls ─────────────────────────────────────────────────────────
        if has_tool_call:
            messages.append(message)

            for tc in message.get("tool_calls", []):
                fn        = tc.get("function", {})
                tool_name = fn.get("name", "")
                yield f"\n*🔍 Looking up: `{tool_name}`...*\n"

                try:
                    tool_input = fn.get("arguments", {})
                    if isinstance(tool_input, str):
                        tool_input = json.loads(tool_input)
                except (json.JSONDecodeError, TypeError):
                    tool_input = {}

                result = _run_tool(tool_name, tool_input)
                messages.append({
                    "role":    "tool",
                    "content": result,
                })
            continue

        # ── Stream final answer ────────────────────────────────────────────────
        stream_response = _ollama_chat(messages, [], stream=True)
        for line in stream_response.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done"):
                    return
            except json.JSONDecodeError:
                continue
        return

    yield "\nI'm sorry, I wasn't able to complete the response. Please try again."


# ── Ollama health check ────────────────────────────────────────────────────────
def check_ollama() -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        log.info(f"Ollama models available: {models}")

        # Check if our model is pulled
        model_base = MODEL.split(":")[0]
        available  = any(model_base in m for m in models)

        if not available:
            print(f"\n⚠️  Model '{MODEL}' not found. Pull it with:")
            print(f"    ollama pull {MODEL}\n")
            return False
        return True
    except requests.exceptions.ConnectionError:
        return False


# ── CLI mode ───────────────────────────────────────────────────────────────────
def run_cli():
    """Interactive CLI tutor session."""

    # Health check
    print("\nChecking Ollama connection...", end="", flush=True)
    if not check_ollama():
        print(f"\n[Error] Ollama is not running or model '{MODEL}' is not available.")
        print("  1. Start Ollama:  ollama serve")
        print(f"  2. Pull model:    ollama pull {MODEL}")
        sys.exit(1)
    print(" ✓")

    print("\n" + "=" * 60)
    print("  🛡️  WebVuln-AI — Web Vulnerability Tutor")
    print(f"  Powered by Ollama + {MODEL} (100% Local)")
    print("=" * 60)
    print("  Try asking:")
    print("  - 'What is SQL Injection?'")
    print("  - 'Quiz me on XSS'")
    print("  - 'How do I prevent CSRF?'")
    print("  - 'List all injection vulnerabilities'")
    print("  Type 'exit' to quit.\n")

    history: list[dict] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("WebVuln-AI: Goodbye! Stay secure 🛡️")
            break

        print("\nWebVuln-AI: ", end="", flush=True)
        try:
            full_response = ""
            for chunk in get_response_streaming(user_input, history):
                print(chunk, end="", flush=True)
                full_response += chunk
            print("\n")

            history.append({"role": "user",     "content": user_input})
            history.append({"role": "assistant", "content": full_response})
            if len(history) > 20:
                history = history[-20:]

        except RuntimeError as e:
            print(f"\n[Error] {e}")
            break
        except Exception as e:
            print(f"\n[Error] {e}")
            log.exception("Agent error")
            continue


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Load .env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    run_cli()