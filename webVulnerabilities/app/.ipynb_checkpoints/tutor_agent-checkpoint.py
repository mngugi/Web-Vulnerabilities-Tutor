import requests
from ollama import client  # make sure Ollama Python SDK is installed

MCP_URL = "http://127.0.0.1:5000/ask"
ollama = client  # Using your local Ollama model

def ask_tutor(question, history=[]):
    """
    Ask the AI tutor a question.
    1. Fetch top vulnerabilities from Flask JSONL API
    2. Include last 10 messages of conversation
    3. Pass context to Ollama and return answer
    """
    # 1️⃣ Query Flask API for top matches
    resp = requests.get(MCP_URL, params={"q": question})
    results = resp.json().get("results", [])

    # 2️⃣ Build context string
    context_text = "\n\n".join([f"{r['title']}: {r['content']}" for r in results])

    # 3️⃣ Include last conversation messages
    conversation = "\n".join(history[-10:]) if history else ""

    # 4️⃣ Build prompt
    prompt = f"""
You are a Web Vulnerability tutor AI. Use the following context to answer the question:

{context_text}

Conversation history:
{conversation}

Question: {question}
Answer:
"""

    # 5️⃣ Query Ollama local model
    response = ollama.chat(messages=[{"role": "user", "content": prompt}])
    answer = response["content"]
    return answer