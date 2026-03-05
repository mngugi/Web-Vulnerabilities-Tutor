import requests

API_URL = "http://127.0.0.1:8000"

def explain_vulnerability():
    vuln = input("Enter vulnerability to explain: ")
    response = requests.post(f"{API_URL}/tutor/explain", json={"vulnerability": vuln})
    print("\nResponse:\n", response.json())

def defence_vulnerability():
    vuln = input("Enter vulnerability to get defence guidance: ")
    response = requests.post(f"{API_URL}/tutor/defence", json={"vulnerability": vuln})
    print("\nResponse:\n", response.json())

def quiz_vulnerability():
    vuln = input("Enter vulnerability to quiz: ")
    response = requests.post(f"{API_URL}/tutor/quiz", json={"vulnerability": vuln})
    print("\nResponse:\n", response.json())

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