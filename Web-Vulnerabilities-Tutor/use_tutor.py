import requests

API_URL = "http://127.0.0.1:8000"

def safe_post(endpoint, vuln):
    """Send POST request safely and handle non-JSON responses."""
    try:
        response = requests.post(f"{API_URL}{endpoint}", json={"vulnerability": vuln})
    except requests.exceptions.RequestException as e:
        print(f"\nError connecting to API: {e}")
        return None

    try:
        return response.json()
    except ValueError:
        # If response is not JSON, show raw text
        print("\nResponse is not JSON, raw response:")
        print(response.text)
        return None

def explain_vulnerability():
    vuln = input("Enter vulnerability to explain: ")
    data = safe_post("/tutor/explain", vuln)
    if data:
        print("\nExplanation:\n", data)

def defence_vulnerability():
    vuln = input("Enter vulnerability to get defence guidance: ")
    data = safe_post("/tutor/defence", vuln)
    if data:
        print("\nDefence Guidance:\n", data)

def quiz_vulnerability():
    vuln = input("Enter vulnerability to quiz: ")
    data = safe_post("/tutor/quiz", vuln)
    if data:
        print("\nQuiz:\n", data)

def main():
    print("=== Web Vulnerabilities Tutor ===")
    while True:
        print("\nOptions:")
        print("1. Explain Vulnerability")
        print("2. Defence Guidance")
        print("3. Quiz")
        print("4. Exit")
        choice = input("Select an option [1-4]: ")
        if choice == "1":
            explain_vulnerability()
        elif choice == "2":
            defence_vulnerability()
        elif choice == "3":
            quiz_vulnerability()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()