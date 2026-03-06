import requests
from ollama import Client

MCP_URL = "http://localhost:5050/query_vulns"

# Connect to local Ollama server
ollama = Client(host="http://localhost:11434")

MODEL = "llama3"   # or mistral / llama2 depending on what you pulled


def ask_tutor(question, history=[]):

    # 1️⃣ Query MCP server for relevant vulnerabilities
    resp = requests.post(MCP_URL, json={"question": question})
    context_docs = resp.json().get("results", [])

    context_text = "\n\n".join(
        [f"{d['title']}: {d['content']}" for d in context_docs]
    )

    # 2️⃣ Include last 10 messages of conversation history
    conversation = "\n".join(history[-10:]) if history else ""

    # 3️⃣ Build prompt
    prompt = f"""
You are a Web Vulnerability tutor AI. Use the following context to answer the question.

Context:
{context_text}

Conversation history:
{conversation}

Question:
{question}

Answer clearly and include examples.
"""

    # 4️⃣ Query Ollama model
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    answer = response["message"]["content"]

    return answer