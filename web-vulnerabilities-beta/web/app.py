from flask import Flask, render_template, request, jsonify, session
from ai_agent.tutor_agent import ask_tutor

app = Flask(__name__)
app.secret_key = "supersecretkey"  # for session-based memory

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    if "history" not in session:
        session["history"] = []

    data = request.json
    question = data.get("question", "")
    answer = ask_tutor(question, session["history"])

    session["history"].append(f"User: {question}")
    session["history"].append(f"Tutor: {answer}")

    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True)