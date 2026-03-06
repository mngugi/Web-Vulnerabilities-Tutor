"""
tutor_agent.py
--------------
WebVuln-AI Tutor Agent

Uses the Anthropic Claude API with MCP tool-use to answer questions about
web vulnerabilities. The agent:
  1. Receives a user message
  2. Calls Claude with the available MCP tools
  3. Executes any tool calls against the MCP server
  4. Streams the final response back

The agent can operate in two modes:
  - CLI mode: interactive terminal session
  - Library mode: call `get_response(user_message, history)` from Flask
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Generator

import anthropic

# ── Path setup ─────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Import tools directly (no TCP needed when running in-process)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp_server"))
from tools import dispatch, get_tool_schemas

# ── Config ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AGENT] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
log = logging.getLogger("tutor_agent")

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 2048
MAX_TOOL_ROUNDS = 5  # max agentic loops before forcing a final answer

SYSTEM_PROMPT = """You are WebVuln-AI, an expert cybersecurity tutor specialising in web application vulnerabilities.

You have access to a structured database of 100+ web vulnerabilities from the WebVuln-Plus project, covering OWASP Top 10 and beyond. Use your tools to fetch accurate, up-to-date information before answering.

Your teaching style:
- Clear and educational — explain concepts at the right level for the student
- Practical — include real examples, PoC scenarios, and tool recommendations
- Structured — use headings, bullet points, and code blocks where helpful
- Safe — always note that PoC payloads are for educational/research purposes only

When a user asks about a vulnerability:
1. Use `get_vulnerability` or `search_vulnerabilities` to fetch precise data
2. Explain the concept in plain language
3. Describe how it works with a concrete example
4. Explain how to detect and mitigate it
5. Suggest testing tools

For quizzes, use `get_quiz_question`. For broad questions, use `list_vulnerabilities` or `get_by_category`.

Always be accurate. If unsure, say so. Never fabricate vulnerability details."""


# ── Build MCP tools for Anthropic API ─────────────────────────────────────────
def _build_anthropic_tools() -> list[dict]:
    """Convert MCP tool schemas to Anthropic tool format."""
    tools = []
    for schema in get_tool_schemas():
        tools.append({
            "name": schema["name"],
            "description": schema["description"],
            "input_schema": schema.get("input_schema", {
                "type": "object",
                "properties": {},
            }),
        })
    return tools


# ── Tool execution ─────────────────────────────────────────────────────────────
def _run_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return the result as a JSON string."""
    log.info(f"Running tool: {tool_name}({list(tool_input.keys())})")
    result = dispatch(tool_name, tool_input)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Core agent loop ────────────────────────────────────────────────────────────
def get_response(
    user_message: str,
    history: list[dict] | None = None,
    stream: bool = False,
) -> str | Generator[str, None, None]:
    """
    Send a message to the tutor agent and get a response.

    Args:
        user_message: The user's question or input.
        history: Previous conversation turns [{"role": ..., "content": ...}].
        stream: If True, yields text chunks as a generator.

    Returns:
        Full response string (stream=False) or generator of chunks (stream=True).
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    tools = _build_anthropic_tools()

    # Build message history
    messages = list(history or [])
    messages.append({"role": "user", "content": user_message})

    # Agentic loop
    for round_num in range(MAX_TOOL_ROUNDS):
        log.info(f"Agent loop round {round_num + 1}/{MAX_TOOL_ROUNDS}")

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        log.info(f"Stop reason: {response.stop_reason}")

        # ── Tool use ───────────────────────────────────────────────────────────
        if response.stop_reason == "tool_use":
            # Add assistant's response (may include text + tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_text = _run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })

            # Add tool results and loop
            messages.append({"role": "user", "content": tool_results})
            continue

        # ── Final answer ───────────────────────────────────────────────────────
        if response.stop_reason in ("end_turn", "max_tokens"):
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            if stream:
                def _gen():
                    yield final_text
                return _gen()
            return final_text

        # Unexpected stop reason
        log.warning(f"Unexpected stop_reason: {response.stop_reason}")
        break

    return "I'm sorry, I wasn't able to complete the response. Please try again."


def get_response_streaming(
    user_message: str,
    history: list[dict] | None = None,
) -> Generator[str, None, None]:
    """
    Streaming version using Anthropic's streaming API.
    Yields text tokens as they arrive, executing tool calls in between rounds.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    tools = _build_anthropic_tools()

    messages = list(history or [])
    messages.append({"role": "user", "content": user_message})

    for round_num in range(MAX_TOOL_ROUNDS):
        collected_content = []
        has_tool_use = False

        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        ) as stream:
            for event in stream:
                # Yield text deltas immediately
                if hasattr(event, "type"):
                    if event.type == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        if delta and hasattr(delta, "text"):
                            yield delta.text

            # Get the final message for tool processing
            final_msg = stream.get_final_message()

        # Check for tool use in final message
        for block in final_msg.content:
            collected_content.append(block)
            if block.type == "tool_use":
                has_tool_use = True

        if has_tool_use:
            messages.append({"role": "assistant", "content": collected_content})
            tool_results = []
            for block in collected_content:
                if block.type == "tool_use":
                    yield f"\n\n*[Fetching: {block.name}...]*\n\n"
                    result_text = _run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # Done
        break


# ── CLI mode ───────────────────────────────────────────────────────────────────
def run_cli():
    """Interactive CLI tutor session."""
    print("\n" + "=" * 60)
    print("  🛡️  WebVuln-AI — Web Vulnerability Tutor (CLI Mode)")
    print("=" * 60)
    print("  Ask about any web vulnerability, or try:")
    print("  - 'What is SQL Injection?'")
    print("  - 'Quiz me on XSS'")
    print("  - 'List all injection vulnerabilities'")
    print("  - 'How do I prevent CSRF?'")
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
            for chunk in get_response_streaming(user_input, history):
                print(chunk, end="", flush=True)
            print("\n")
        except anthropic.AuthenticationError:
            print("\n[Error] Invalid ANTHROPIC_API_KEY. Set it in your .env file.")
            break
        except Exception as e:
            print(f"\n[Error] {e}")
            log.exception("Agent error")
            continue

        # Update history (simplified — store last 10 turns)
        history.append({"role": "user", "content": user_input})
        # Note: for real history we'd store the assistant response too
        # This is handled by get_response_streaming internally
        if len(history) > 20:
            history = history[-20:]


if __name__ == "__main__":
    # Load .env if available
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    run_cli()