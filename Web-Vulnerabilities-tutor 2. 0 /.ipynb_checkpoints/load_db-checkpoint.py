import os
import sqlite3

DATA_DIR = "data/vulnerabilities"  # path to your cloned repo

# 1️⃣ Connect to SQLite database
conn = sqlite3.connect("webvuln_dataset.db")
cur = conn.cursor()

# 2️⃣ Create table
cur.execute("""
CREATE TABLE IF NOT EXISTS vulnerabilities (
    id INTEGER PRIMARY KEY,
    filename TEXT UNIQUE,
    title TEXT,
    content TEXT,
    tags TEXT
)
""")

# 3️⃣ Load markdown files
for fname in sorted(os.listdir(DATA_DIR)):
    if fname.endswith(".md"):
        with open(os.path.join(DATA_DIR, fname), "r", encoding="utf-8") as f:
            content = f.read()
            # Use first line as title
            lines = content.splitlines()
            title = lines[0].strip("# ").strip() if lines else fname
            cur.execute("INSERT OR IGNORE INTO vulnerabilities (filename, title, content) VALUES (?, ?, ?)",
                        (fname, title, content))

# 4️⃣ Commit and close
conn.commit()
conn.close()
print("Database created: webvuln_dataset.db")