import anthropic

client = anthropic.Anthropic()

def explain_vulnerability(text):

    prompt = f"""
You are a cybersecurity tutor.

Explain this vulnerability clearly:

{text}

Include:
1. What it is
2. Attack example
3. Real-world case
4. Defense techniques
"""

    response = client.messages.create(
        model="claude-3-sonnet",
        max_tokens=800,
        messages=[{"role":"user","content":prompt}]
    )

    return response.content[0].text