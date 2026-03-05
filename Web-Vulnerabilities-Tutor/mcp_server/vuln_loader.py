import os

DATA_PATH = "data/vulnerabilities"

def list_vulns():
    files = sorted(os.listdir(DATA_PATH))
    return files

def get_vuln(vuln_id):
    files = sorted(os.listdir(DATA_PATH))
    file = files[vuln_id - 1]

    with open(os.path.join(DATA_PATH, file)) as f:
        return f.read()