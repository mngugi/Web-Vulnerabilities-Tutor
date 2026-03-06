"""
vuln_loader.py
--------------
Parses the WebVuln--Plus dataset (README.md) from data/vulnerabilities/
and returns structured vulnerability objects for use by the MCP tools.

The dataset is a single large README.md with entries like:
  WEBVULN-001: SQL Injection
  WEBVULN-002: XSS
  ...through WEBVULN-100

Each entry has: category, description, PoC, mitigation, tools, references.
"""

import os
import re
import json
from typing import Optional

# ── Path config ────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "vulnerabilities"
)
README_PATH = os.path.join(DATA_DIR, "README.md")

# ── In-memory cache ────────────────────────────────────────────────────────────
_VULN_DB: dict[str, dict] = {}
_LOADED = False


# ── Data structures ────────────────────────────────────────────────────────────
def _empty_vuln(vuln_id: str, name: str) -> dict:
    return {
        "id": vuln_id,          # e.g. "WEBVULN-001"
        "name": name,           # e.g. "SQL Injection"
        "category": "",
        "description": "",
        "poc": "",
        "payloads": [],
        "mitigation": [],
        "tools": [],
        "references": [],
        "difficulty": _infer_difficulty(vuln_id),
    }


def _infer_difficulty(vuln_id: str) -> str:
    """Rough difficulty heuristic based on ID range."""
    try:
        num = int(vuln_id.split("-")[1])
    except (IndexError, ValueError):
        return "Intermediate"
    if num <= 20:
        return "Beginner"
    elif num <= 60:
        return "Intermediate"
    return "Advanced"


# ── Parser ─────────────────────────────────────────────────────────────────────
def _parse_readme(path: str) -> dict[str, dict]:
    """
    Reads the README.md and splits it into per-vulnerability blocks.
    Returns a dict keyed by WEBVULN-NNN.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset not found at {path}.\n"
            "Run: git clone https://github.com/mngugi/WebVuln--Plus data/vulnerabilities"
        )

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    db: dict[str, dict] = {}

    # Split on vulnerability ID headers — match "WEBVULN-NNN" headings
    # Patterns used in the doc: "WEBVULN-001:", "#NNN:", "Web Vulnerability #NN:"
    pattern = re.compile(
        r'(?:(?:#+\s*)?(?:🛡️\s*|🌐\s*)?(?:Web\s+Vulnerability\s+#?|WEBVULN-))(\d+)[:\s]([^\n]+)',
        re.IGNORECASE
    )

    matches = list(pattern.finditer(content))

    for i, match in enumerate(matches):
        num_str = match.group(1).zfill(3)
        raw_name = match.group(2).strip()
        # Clean emoji and common prefixes from name
        name = re.sub(r'[^\w\s\-\(\)/]+', '', raw_name).strip()
        name = re.sub(r'\s+', ' ', name)

        vuln_id = f"WEBVULN-{num_str}"

        # Extract the block between this heading and the next
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        block = content[start:end]

        v = _empty_vuln(vuln_id, name)

        # -- Category --
        cat_match = re.search(r'[Cc]ategory[:\s]*\n?\s*([^\n]+)', block)
        if cat_match:
            v["category"] = cat_match.group(1).strip().lstrip('#').strip()

        # -- Description --
        desc_match = re.search(
            r'(?:Description|Overview|Vulnerability Overview)[:\s]*\n([\s\S]+?)(?=\n#{1,4}\s|\n🧪|\n💣|\n🛡️|\n🔒|\Z)',
            block, re.IGNORECASE
        )
        if desc_match:
            v["description"] = desc_match.group(1).strip()[:1500]

        # -- PoC block --
        poc_match = re.search(
            r'(?:Proof of Concept|PoC|Demo)[^\n]*\n([\s\S]+?)(?=\n#{1,4}\s|\n🛡️|\n🔒|\n🔧|\Z)',
            block, re.IGNORECASE
        )
        if poc_match:
            v["poc"] = poc_match.group(1).strip()[:2000]

        # -- Payloads: extract inline code blocks ──
        v["payloads"] = re.findall(r'`([^`\n]{5,120})`', block)[:10]

        # -- Mitigation bullet points --
        mit_match = re.search(
            r'(?:Mitigation|Prevention)[^\n]*\n([\s\S]+?)(?=\n#{1,4}\s|\n🔧|\n🧪|\n📚|\Z)',
            block, re.IGNORECASE
        )
        if mit_match:
            mit_text = mit_match.group(1)
            bullets = re.findall(r'(?:✅|[-*•])\s+([^\n]+)', mit_text)
            v["mitigation"] = [b.strip() for b in bullets if len(b.strip()) > 5][:10]
            if not v["mitigation"]:
                v["mitigation"] = [l.strip() for l in mit_text.splitlines()
                                   if l.strip() and not l.startswith('#')][:8]

        # -- Tools --
        tools_match = re.search(
            r'(?:Testing Tools|Tools)[^\n]*\n([\s\S]+?)(?=\n#{1,4}\s|\n📚|\n🔗|\Z)',
            block, re.IGNORECASE
        )
        if tools_match:
            tool_lines = re.findall(r'[-*]\s+([^\n]+)', tools_match.group(1))
            v["tools"] = [t.strip() for t in tool_lines if len(t.strip()) > 2][:8]

        # -- References --
        refs = re.findall(r'https?://[^\s\)>\]"]+', block)
        v["references"] = list(dict.fromkeys(refs))[:8]  # dedupe, keep order

        # Avoid duplicates — keep first occurrence
        if vuln_id not in db:
            db[vuln_id] = v

    return db


# ── Public API ─────────────────────────────────────────────────────────────────
def load_vulnerabilities(force: bool = False) -> dict[str, dict]:
    """
    Load and cache all vulnerabilities from the dataset.
    Returns dict keyed by WEBVULN-NNN.
    """
    global _VULN_DB, _LOADED
    if _LOADED and not force:
        return _VULN_DB
    try:
        _VULN_DB = _parse_readme(README_PATH)
        _LOADED = True
        print(f"[vuln_loader] Loaded {len(_VULN_DB)} vulnerabilities from dataset.")
    except FileNotFoundError as e:
        print(f"[vuln_loader] WARNING: {e}")
        _VULN_DB = {}
        _LOADED = True
    return _VULN_DB


def get_vulnerability(vuln_id: str) -> Optional[dict]:
    """Fetch a single vulnerability by ID (case-insensitive)."""
    db = load_vulnerabilities()
    key = vuln_id.upper()
    # Try exact match
    if key in db:
        return db[key]
    # Try padding: WEBVULN-1 → WEBVULN-001
    m = re.match(r'WEBVULN-(\d+)', key)
    if m:
        padded = f"WEBVULN-{int(m.group(1)):03d}"
        return db.get(padded)
    return None


def search_vulnerabilities(query: str) -> list[dict]:
    """Full-text search across name, description, category."""
    db = load_vulnerabilities()
    q = query.lower()
    results = []
    for v in db.values():
        haystack = " ".join([
            v.get("name", ""),
            v.get("category", ""),
            v.get("description", ""),
        ]).lower()
        if q in haystack:
            results.append(v)
    return results


def list_all(fields: list[str] = None) -> list[dict]:
    """Return all vulnerabilities, optionally projecting to specific fields."""
    db = load_vulnerabilities()
    if not fields:
        return list(db.values())
    return [{f: v.get(f, "") for f in fields} for v in db.values()]


def get_by_category(category: str) -> list[dict]:
    """Return all vulns whose category matches (case-insensitive substring)."""
    db = load_vulnerabilities()
    cat = category.lower()
    return [v for v in db.values() if cat in v.get("category", "").lower()]


def list_categories() -> list[str]:
    """Return deduplicated list of categories."""
    db = load_vulnerabilities()
    cats = sorted({v["category"] for v in db.values() if v["category"]})
    return cats


def get_stats() -> dict:
    """Return summary statistics about the dataset."""
    db = load_vulnerabilities()
    cats = {}
    diffs = {"Beginner": 0, "Intermediate": 0, "Advanced": 0}
    for v in db.values():
        cats[v["category"]] = cats.get(v["category"], 0) + 1
        diffs[v["difficulty"]] = diffs.get(v["difficulty"], 0) + 1
    return {
        "total": len(db),
        "categories": cats,
        "difficulty_breakdown": diffs,
    }


# ── CLI test ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    db = load_vulnerabilities()
    print(f"\nTotal vulnerabilities: {len(db)}")
    stats = get_stats()
    print(f"Difficulty: {stats['difficulty_breakdown']}")
    print(f"\nSample - WEBVULN-001:")
    v = get_vulnerability("WEBVULN-001")
    if v:
        print(json.dumps(v, indent=2, default=str)[:800])