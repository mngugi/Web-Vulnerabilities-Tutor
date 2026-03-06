import requests
from ollama import Ollama

MCP_URL = "http://localhost:5050/query_vulns"
ollama = Ollama(model="llama2")  # Adjust model name as needed

def ask_tutor(question, history=[]):
    # 1️⃣ Get top relevant vulnerabilities from MCP server
    resp = requests.post(MCP_URL, json={"question": question})
    context_docs = resp.json().get("results", [])
    context_text = "\n\n".join([f"{d['title']}: {d['content']}" for d in context_docs])

    # 2️⃣ Include conversation history (last 10 messages)
    conversation = "\n".join(history[-10:]) if history else ""

    # 3️⃣ Build prompt for Ollama
    prompt = f"""
You are a Web Vulnerability tutor AI. Use the following context to answer the question:

{context_text}

Conversation history:
{conversation}

Question: {question}
Answer:
"""

    # 4️⃣ Query Ollama
    response = ollama.chat(messages=[{"role": "user", "content": prompt}])
    answer = response["content"]
    return answer