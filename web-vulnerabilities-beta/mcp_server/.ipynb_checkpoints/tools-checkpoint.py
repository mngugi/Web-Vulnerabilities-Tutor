import sqlite3

DB_PATH = "data/vulnerabilities.db"

def search_vulnerabilities(question):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    keyword = f"%{question}%"

    cursor.execute("""
        SELECT title, content
        FROM vulnerabilities
        WHERE title LIKE ?
        OR content LIKE ?
        LIMIT 5
    """, (keyword, keyword))

    rows = cursor.fetchall()

    conn.close()

    results = []

    for r in rows:
        results.append({
            "title": r[0],
            "content": r[1]
        })

    return results