import os
import json
from ollama import Client

# Instantiate Ollama client
ollama = Client()

# Use the actual local model installed
MODEL_NAME = "llama3.2:latest"

# Path to local data
DATA_FILE = os.path.join("data", "vulnerabilities.json")
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        LOCAL_DATA = json.load(f)
else:
    LOCAL_DATA = []

def ask_tutor(question, history=[]):
    """
    Ask the AI tutor using local data + conversation history
    """
    # 1️⃣ Build context from local vulnerability data
    context_text = "\n\n".join([f"{r['title']}: {r['content']}" for r in LOCAL_DATA])

    # 2️⃣ Include last conversation messages
    conversation = "\n".join(history[-10:]) if history else ""

    # 3️⃣ Build the prompt for the AI
    prompt = f"""
You are a Web Vulnerability tutor AI. Use the following context to answer the question:

{context_text}

Conversation history:
{conversation}

Question: {question}
Answer:
"""

    # 4️⃣ Query Ollama local model
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        # Ollama SDK returns a dict with 'content'
        answer = response.get("content", "No answer returned")
    except Exception as e:
        answer = f"Error communicating with Ollama: {str(e)}"

    return answer