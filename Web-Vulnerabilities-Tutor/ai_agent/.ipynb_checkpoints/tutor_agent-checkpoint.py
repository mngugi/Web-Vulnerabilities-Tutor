import anthropic

client = anthropic.Anthropic()

class TutorAgent:

    def explain(self, vulnerability):

        prompt = f"""
Explain this vulnerability:

{vulnerability}

Include:
1. What it is
2. Attack example
3. Real-world case
4. Defense techniques
"""

        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )

        return {"lesson": response.content[0].text}


    def defence(self, vulnerability):
        return {"defence": f"Defence techniques for {vulnerability}"}


    def quiz(self, vulnerability):
        return {"quiz": f"What is the main risk of {vulnerability}?"}


tutor = TutorAgent()