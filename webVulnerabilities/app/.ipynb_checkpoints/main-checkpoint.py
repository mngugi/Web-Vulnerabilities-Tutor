from flask import Flask, request, jsonify
from .tutor_agent import ask_tutor

app = Flask(__name__)

# Simple health check
@app.route("/")
def home():
    return jsonify({"message": "Web Vulnerabilities Beta API running"})

# Main tutor route
@app.route("/ask_tutor", methods=["GET"])
def ask_tutor_route():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    # Call the AI tutor
    answer = ask_tutor(query)

    return jsonify({
        "query": query,
        "answer": answer
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)