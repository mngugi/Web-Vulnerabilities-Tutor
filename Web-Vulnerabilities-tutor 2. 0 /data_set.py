import os
import json

DATA_DIR = "data/vulnerabilities"
dataset = []

for fname in sorted(os.listdir(DATA_DIR)):
    if fname.endswith(".md"):
        with open(os.path.join(DATA_DIR, fname), "r", encoding="utf-8") as f:
            content = f.read()
            title = content.splitlines()[0].strip("# ").strip() if content else fname
            dataset.append({
                "filename": fname,
                "title": title,
                "content": content,
                "tags": ""
            })

# Save as JSONL (one document per line)
with open("webvuln_dataset.jsonl", "w", encoding="utf-8") as f:
    for item in dataset:
        f.write(json.dumps(item) + "\n")