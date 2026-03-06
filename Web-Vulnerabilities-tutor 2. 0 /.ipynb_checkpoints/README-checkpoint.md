# 🛡️ WebVuln-AI — Web Vulnerability AI Tutor

An AI-powered cybersecurity tutor that uses the **Model Context Protocol (MCP)** to serve web vulnerability data and an **AI agent** to teach, explain, and quiz users on common web vulnerabilities — powered by the [WebVuln--Plus](https://github.com/mngugi/WebVuln--Plus) dataset.

---

## 📁 Project Structure

```
webvuln-ai/
├── mcp_server/
│   ├── server.py           # MCP server — exposes vulnerability data as tools
│   ├── vuln_loader.py      # Loads and parses vulnerability data from /data
│   └── tools.py            # Tool definitions for the MCP server
│
├── ai_agent/
│   └── tutor_agent.py      # AI tutor agent — queries MCP, teaches via Claude
│
├── web/
│   ├── app.py              # Flask web application
│   └── templates/          # HTML templates for the web UI
│
├── data/
│   └── vulnerabilities/    # Cloned WebVuln--Plus repo (vulnerability dataset)
│
├── requirements.txt        # Python dependencies
├── run.sh                  # One-command setup and launch script
└── README.md               # This file
```

---

## 🚀 Quickstart

### 1. Clone this repo and the dataset

```bash
git clone https://github.com/mngugi/WebVuln--Plus.webvuln-ai.git
cd WebVuln--Plus.webvuln-ai

# Clone the vulnerability dataset into /data/vulnerabilities
git clone https://github.com/mngugi/WebVuln--Plus data/vulnerabilities
```

### 2. Run the project

```bash
chmod +x run.sh
./run.sh
```

This will:
- Create a Python virtual environment
- Install all dependencies from `requirements.txt`
- Start the MCP server
- Launch the Flask web app

### 3. Open your browser

```
http://localhost:5000
```

---

## 🧠 How It Works

```
User (Browser)
     │
     ▼
Flask Web App  (web/app.py)
     │
     ▼
AI Tutor Agent  (ai_agent/tutor_agent.py)
     │  Uses Claude API + MCP tool calls
     ▼
MCP Server  (mcp_server/server.py)
     │  Calls tools defined in tools.py
     ▼
Vuln Loader  (mcp_server/vuln_loader.py)
     │  Reads structured JSON/YAML/MD files
     ▼
data/vulnerabilities/  ← WebVuln--Plus dataset
```

1. The **MCP server** exposes vulnerability entries as callable tools (e.g., `get_vuln_by_name`, `list_categories`, `get_example_payload`).
2. The **AI tutor agent** uses Claude with MCP tool-use to fetch relevant data and respond to user questions in an educational format.
3. The **Flask app** provides the chat interface where users interact with the tutor.

---

## 📦 Dependencies

See [`requirements.txt`](./requirements.txt) for the full list. Key packages:

| Package | Purpose |
|---|---|
| `flask` | Web server / UI |
| `anthropic` | Claude API client |
| `mcp` | Model Context Protocol SDK |
| `pyyaml` | Parse YAML vulnerability files |
| `python-dotenv` | Manage API keys via `.env` |

---

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_api_key_here
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8765
FLASK_PORT=5000
FLASK_DEBUG=true
```

> ⚠️ Never commit your `.env` file. It is listed in `.gitignore`.

---

## 🗂️ Dataset — WebVuln--Plus

The vulnerability data lives in `data/vulnerabilities/` and is sourced from the [WebVuln--Plus](https://github.com/mngugi/WebVuln--Plus) repository.

It covers:

- **OWASP Top 10** vulnerabilities
- SQL Injection, XSS, CSRF, IDOR, SSRF, XXE, RCE, and more
- Descriptions, example payloads, mitigation strategies
- Difficulty levels: Beginner / Intermediate / Advanced

---

## 🧩 MCP Tools Exposed

| Tool Name | Description |
|---|---|
| `list_vulnerabilities` | Returns all vulnerability names and categories |
| `get_vulnerability` | Returns full details for a named vulnerability |
| `list_categories` | Returns all vulnerability categories |
| `get_by_category` | Returns all vulns in a given category |
| `get_example_payload` | Returns example attack payloads |
| `get_mitigation` | Returns mitigation strategies |
| `get_quiz_question` | Returns a quiz question on a topic |

---

## 🛠️ Development

### Run components individually

```bash
# Start MCP server only
python mcp_server/server.py

# Start Flask web app only
python web/app.py

# Run the agent in CLI mode
python ai_agent/tutor_agent.py
```

### Run tests (coming soon)

```bash
pytest tests/
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push and open a PR

---

## 📄 License

MIT License — see [LICENSE](./LICENSE) for details.

---

## 👤 Author

**M. Ngugi** — [@mngugi](https://github.com/mngugi)

Built with ❤️ using Claude (Anthropic), MCP, and the WebVuln--Plus dataset.