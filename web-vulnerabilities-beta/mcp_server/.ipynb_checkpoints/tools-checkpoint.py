import sqlite3

DB_PATH = "data/webvuln_dataset.db"

def search_vulnerabilities(keyword, limit=5):
    """
    Search vulnerabilities in the DB by keyword.
    Returns a list of dicts: {"title": ..., "content": ...}
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT title, content FROM vulnerabilities WHERE title LIKE ? OR content LIKE ? LIMIT ?",
        (f"%{keyword}%", f"%{keyword}%", limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [{"title": r[0], "content": r[1]} for r in rows]