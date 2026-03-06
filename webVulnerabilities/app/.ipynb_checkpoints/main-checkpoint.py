from flask import Flask, request, jsonify
from .search import search_vulnerability
from .tutor_agent import ask_tutor   # <-- updated import

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "Web Vulnerabilities Beta API running"})

@app.route("/ask_tutor", methods=["GET"])
def ask_tutor_route():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    answer = ask_tutor(query)
    return jsonify({
        "query": query,
        "answer": answer
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)