from flask import Flask, request, jsonify
from mcp_server.tools import search_vulnerabilities

app = Flask(__name__)

@app.route("/query_vulns", methods=["POST"])
def query_vulns():

    data = request.json
    question = data.get("question", "")

    results = search_vulnerabilities(question)

    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(port=5050)