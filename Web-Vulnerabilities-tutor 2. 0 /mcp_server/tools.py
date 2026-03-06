"""
tools.py
--------
Defines all MCP tool schemas and their handler functions.
Each tool receives validated arguments and returns a plain Python dict
that the MCP server serialises to JSON for the AI agent.
"""

from __future__ import annotations
import random
from typing import Any
from vuln_loader import (
    get_vulnerability,
    search_vulnerabilities,
    list_all,
    get_by_category,
    list_categories,
    get_stats,
    load_vulnerabilities,
)

# ── Tool registry ──────────────────────────────────────────────────────────────
# Each entry: { "schema": <MCP tool schema dict>, "handler": <callable> }
TOOLS: list[dict] = []


def _register(schema: dict):
    """Decorator — registers a function as an MCP tool."""
    def decorator(fn):
        TOOLS.append({"schema": schema, "handler": fn})
        return fn
    return decorator


# ──────────────────────────────────────────────────────────────────────────────
# Tool 1 — list_vulnerabilities
# ──────────────────────────────────────────────────────────────────────────────
@_register({
    "name": "list_vulnerabilities",
    "description": (
        "Return a summary list of all web vulnerabilities in the dataset. "
        "Each entry includes the ID, name, category, and difficulty level."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max number of results to return (default 100).",
                "default": 100,
            }
        },
        "required": [],
    },
})
def list_vulnerabilities(limit: int = 100, **_) -> dict:
    vulns = list_all(fields=["id", "name", "category", "difficulty"])
    return {
        "total": len(vulns),
        "vulnerabilities": vulns[:limit],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Tool 2 — get_vulnerability
# ──────────────────────────────────────────────────────────────────────────────
@_register({
    "name": "get_vulnerability",
    "description": (
        "Return the full details for a single vulnerability by its ID "
        "(e.g. 'WEBVULN-001') or by name keyword (e.g. 'SQL Injection'). "
        "Includes description, PoC scenario, mitigation steps, tools, and references."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Vulnerability ID (WEBVULN-NNN) or name keyword.",
            }
        },
        "required": ["query"],
    },
})
def get_vulnerability_tool(query: str, **_) -> dict:
    # Try by ID first
    vuln = get_vulnerability(query.strip().upper())
    if not vuln:
        # Fall back to name search
        results = search_vulnerabilities(query)
        if results:
            vuln = results[0]
    if not vuln:
        return {"error": f"No vulnerability found matching '{query}'."}
    return vuln


# ──────────────────────────────────────────────────────────────────────────────
# Tool 3 — list_categories
# ──────────────────────────────────────────────────────────────────────────────
@_register({
    "name": "list_categories",
    "description": "Return all vulnerability categories present in the dataset.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def list_categories_tool(**_) -> dict:
    cats = list_categories()
    return {"categories": cats, "count": len(cats)}


# ──────────────────────────────────────────────────────────────────────────────
# Tool 4 — get_by_category
# ──────────────────────────────────────────────────────────────────────────────
@_register({
    "name": "get_by_category",
    "description": (
        "Return all vulnerabilities that belong to a given category. "
        "Example categories: 'Injection', 'Authentication', 'Access Control'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Category name or substring (case-insensitive).",
            }
        },
        "required": ["category"],
    },
})
def get_by_category_tool(category: str, **_) -> dict:
    vulns = get_by_category(category)
    if not vulns:
        return {"error": f"No vulnerabilities found in category '{category}'."}
    return {
        "category": category,
        "count": len(vulns),
        "vulnerabilities": [
            {"id": v["id"], "name": v["name"], "difficulty": v["difficulty"]}
            for v in vulns
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Tool 5 — get_example_payload
# ──────────────────────────────────────────────────────────────────────────────
@_register({
    "name": "get_example_payload",
    "description": (
        "Return example attack payloads for a vulnerability. "
        "Useful for understanding what malicious input looks like. "
        "Educational use only."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Vulnerability ID or name keyword.",
            }
        },
        "required": ["query"],
    },
})
def get_example_payload(query: str, **_) -> dict:
    vuln = get_vulnerability(query.upper())
    if not vuln:
        results = search_vulnerabilities(query)
        vuln = results[0] if results else None
    if not vuln:
        return {"error": f"No vulnerability found matching '{query}'."}

    payloads = vuln.get("payloads", [])
    poc_snippet = vuln.get("poc", "")[:500]

    return {
        "id": vuln["id"],
        "name": vuln["name"],
        "payloads": payloads if payloads else ["No inline payloads extracted — see PoC."],
        "poc_excerpt": poc_snippet,
        "disclaimer": "For educational and security research purposes only.",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Tool 6 — get_mitigation
# ──────────────────────────────────────────────────────────────────────────────
@_register({
    "name": "get_mitigation",
    "description": (
        "Return the mitigation strategies for a given vulnerability. "
        "Useful when teaching how to fix or prevent the vulnerability."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Vulnerability ID or name keyword.",
            }
        },
        "required": ["query"],
    },
})
def get_mitigation(query: str, **_) -> dict:
    vuln = get_vulnerability(query.upper())
    if not vuln:
        results = search_vulnerabilities(query)
        vuln = results[0] if results else None
    if not vuln:
        return {"error": f"No vulnerability found matching '{query}'."}

    mitigations = vuln.get("mitigation", [])
    tools = vuln.get("tools", [])
    refs = vuln.get("references", [])

    return {
        "id": vuln["id"],
        "name": vuln["name"],
        "mitigation_steps": mitigations if mitigations else ["See vulnerability description for details."],
        "testing_tools": tools,
        "references": refs,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Tool 7 — get_quiz_question
# ──────────────────────────────────────────────────────────────────────────────
_QUESTION_TEMPLATES = [
    ("What is {name} and how does it work?",                   "conceptual"),
    ("What are the main mitigation strategies for {name}?",    "mitigation"),
    ("In what category does {name} belong?",                   "category"),
    ("What tools are typically used to test for {name}?",      "tools"),
    ("Describe a real-world attack scenario involving {name}.", "scenario"),
    ("How does {name} differ from other injection attacks?",   "comparison"),
    ("What is the OWASP classification for {name}?",           "classification"),
]


@_register({
    "name": "get_quiz_question",
    "description": (
        "Generate a quiz question about a web vulnerability for educational purposes. "
        "Optionally specify a topic or leave blank for a random vulnerability."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Vulnerability ID, name, or category. Leave blank for random.",
                "default": "",
            },
            "difficulty": {
                "type": "string",
                "enum": ["Beginner", "Intermediate", "Advanced"],
                "description": "Filter by difficulty level.",
                "default": "",
            },
        },
        "required": [],
    },
})
def get_quiz_question(topic: str = "", difficulty: str = "", **_) -> dict:
    db = load_vulnerabilities()
    vulns = list(db.values())

    # Filter by difficulty
    if difficulty:
        vulns = [v for v in vulns if v.get("difficulty", "").lower() == difficulty.lower()]

    # Filter by topic
    if topic:
        matched = search_vulnerabilities(topic)
        if matched:
            vulns = matched

    if not vulns:
        return {"error": "No matching vulnerabilities found for quiz."}

    vuln = random.choice(vulns)
    template, q_type = random.choice(_QUESTION_TEMPLATES)
    question = template.format(name=vuln["name"])

    # Build answer hint based on question type
    if q_type == "mitigation":
        answer_hint = "; ".join(vuln.get("mitigation", [])[:3]) or "See mitigation section."
    elif q_type == "category":
        answer_hint = vuln.get("category", "Unknown")
    elif q_type == "tools":
        answer_hint = ", ".join(vuln.get("tools", [])[:4]) or "See tools section."
    else:
        answer_hint = vuln.get("description", "")[:300] or "See description."

    return {
        "vuln_id": vuln["id"],
        "vuln_name": vuln["name"],
        "difficulty": vuln["difficulty"],
        "question": question,
        "question_type": q_type,
        "answer_hint": answer_hint,
        "category": vuln["category"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Tool 8 — search_vulnerabilities
# ──────────────────────────────────────────────────────────────────────────────
@_register({
    "name": "search_vulnerabilities",
    "description": "Full-text search across vulnerability names, descriptions, and categories.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search term (e.g. 'session', 'token', 'header').",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default 10).",
                "default": 10,
            },
        },
        "required": ["query"],
    },
})
def search_tool(query: str, limit: int = 10, **_) -> dict:
    results = search_vulnerabilities(query)
    trimmed = [
        {"id": v["id"], "name": v["name"], "category": v["category"], "difficulty": v["difficulty"]}
        for v in results[:limit]
    ]
    return {
        "query": query,
        "count": len(trimmed),
        "results": trimmed,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Tool 9 — get_dataset_stats
# ──────────────────────────────────────────────────────────────────────────────
@_register({
    "name": "get_dataset_stats",
    "description": "Return statistics about the vulnerability dataset: total count, categories, and difficulty breakdown.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def get_dataset_stats(**_) -> dict:
    return get_stats()


# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────────────────────────────────────
_HANDLER_MAP: dict[str, Any] = {
    t["schema"]["name"]: t["handler"] for t in TOOLS
}


def dispatch(tool_name: str, tool_input: dict) -> dict:
    """
    Dispatch a tool call by name with the provided input dict.
    Returns a result dict or an error dict.
    """
    handler = _HANDLER_MAP.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: '{tool_name}'"}
    try:
        return handler(**tool_input)
    except Exception as e:
        return {"error": f"Tool '{tool_name}' raised an exception: {str(e)}"}


def get_tool_schemas() -> list[dict]:
    """Return all MCP tool schemas for registration with the server."""
    return [t["schema"] for t in TOOLS]