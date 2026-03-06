from flask import Flask, request, jsonify
import ollama

app = Flask(__name__)

@app.route("/")
def home():
    return "🛡️ WebVuln-AI running"

@app.route("/ask")
def ask():
    question = request.args.get("q")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "user", "content": question}
        ]
    )

    answer = response["message"]["content"]

    return jsonify({
        "question": question,
        "answer": answer
    })

if __name__ == "__main__":
    app.run(debug=True)