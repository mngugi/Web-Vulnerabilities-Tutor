from flask import Flask, request, jsonify
from .search import search_vulnerability

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "Web Vulnerabilities Beta API running"})

@app.route("/ask", methods=["GET"])
def ask():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    results = search_vulnerability(query)
    return jsonify({
        "query": query,
        "results": results
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)