import os
import json
from ollama import Client

# Instantiate Ollama client
ollama = Client()

# Use your actual Ollama model
MODEL_NAME = "llama3.2:latest"

# Load local vulnerability data if available
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
    # 1️⃣ Build context from local data
    context_text = "\n\n".join([f"{r['title']}: {r['content']}" for r in LOCAL_DATA])
    if not context_text:
        context_text = "No local vulnerability data available."

    # 2️⃣ Include last 10 conversation messages
    conversation = "\n".join(history[-10:]) if history else ""

    # 3️⃣ Build the prompt
    prompt = f"""
Use the context below to answer the user's question.

Context:
{context_text}

Conversation history:
{conversation}

Question: {question}
Answer:
"""

    # 4️⃣ Query Ollama
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a knowledgeable Web Vulnerability tutor. Answer clearly and concisely."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.get("content", "No answer returned")
    except Exception as e:
        answer = f"Error communicating with Ollama: {str(e)}"

    return answer