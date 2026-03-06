import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "webvuln_dataset.jsonl"

# Load all vulnerabilities into memory at startup
with open(DATA_PATH, "r", encoding="utf-8") as f:
    VULNS = [json.loads(line) for line in f]

def search_vulnerability(query, max_results=5):
    """
    Simple keyword search in title or content
    Returns top max_results matches
    """
    query_lower = query.lower()
    results = []

    for vuln in VULNS:
        title = vuln.get("title","").lower()
        content = vuln.get("content","").lower()

        if query_lower in title or query_lower in content:
            results.append(vuln)
            if len(results) >= max_results:
                break

    return results