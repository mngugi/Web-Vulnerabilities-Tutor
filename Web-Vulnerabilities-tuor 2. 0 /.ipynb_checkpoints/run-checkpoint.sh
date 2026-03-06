#!/usr/bin/env bash
# =============================================================================
# run.sh — WebVuln-AI Setup & Launch Script
# Clones the WebVuln--Plus dataset, installs dependencies, and starts all
# components: MCP server + Flask web app.
# =============================================================================

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Config ────────────────────────────────────────────────────────────────────
VENV_DIR=".venv"
DATA_DIR="data/vulnerabilities"
DATASET_REPO="https://github.com/mngugi/WebVuln--Plus"
MCP_HOST="${MCP_SERVER_HOST:-localhost}"
MCP_PORT="${MCP_SERVER_PORT:-8765}"
FLASK_PORT="${FLASK_PORT:-5000}"
REQUIREMENTS="requirements.txt"
ENV_FILE=".env"

# ── Helpers ───────────────────────────────────────────────────────────────────
log()    { echo -e "${GREEN}[✔]${NC} $1"; }
info()   { echo -e "${BLUE}[→]${NC} $1"; }
warn()   { echo -e "${YELLOW}[!]${NC} $1"; }
error()  { echo -e "${RED}[✘]${NC} $1"; exit 1; }
header() { echo -e "\n${BOLD}${BLUE}$1${NC}\n"; }

# Trap to kill background processes on exit
cleanup() {
  header "Shutting down..."
  if [[ -n "${MCP_PID:-}" ]]; then
    kill "$MCP_PID" 2>/dev/null && log "MCP server stopped (PID $MCP_PID)"
  fi
  if [[ -n "${FLASK_PID:-}" ]]; then
    kill "$FLASK_PID" 2>/dev/null && log "Flask app stopped (PID $FLASK_PID)"
  fi
}
trap cleanup EXIT INT TERM

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "${BOLD}"
echo "  ██╗    ██╗███████╗██████╗ ██╗   ██╗██╗     ███╗   ██╗"
echo "  ██║    ██║██╔════╝██╔══██╗██║   ██║██║     ████╗  ██║"
echo "  ██║ █╗ ██║█████╗  ██████╔╝██║   ██║██║     ██╔██╗ ██║"
echo "  ██║███╗██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║     ██║╚██╗██║"
echo "  ╚███╔███╔╝███████╗██████╔╝ ╚████╔╝ ███████╗██║ ╚████║"
echo "   ╚══╝╚══╝ ╚══════╝╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═══╝"
echo ""
echo "             🛡️  WebVuln-AI — Web Vulnerability Tutor"
echo -e "${NC}"

# ── Step 1: Check prerequisites ───────────────────────────────────────────────
header "Step 1: Checking prerequisites"

command -v python3 >/dev/null 2>&1 || error "python3 is not installed. Please install Python 3.10+"
command -v pip3 >/dev/null 2>&1    || error "pip3 is not installed."
command -v git >/dev/null 2>&1     || error "git is not installed."

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_MAJOR=3
REQUIRED_MINOR=10

MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [[ "$MAJOR" -lt "$REQUIRED_MAJOR" ]] || { [[ "$MAJOR" -eq "$REQUIRED_MAJOR" ]] && [[ "$MINOR" -lt "$REQUIRED_MINOR" ]]; }; then
  error "Python 3.10+ required, found Python $PYTHON_VERSION"
fi

log "Python $PYTHON_VERSION detected"
log "git $(git --version | awk '{print $3}') detected"

# ── Step 2: Check .env file ───────────────────────────────────────────────────
header "Step 2: Environment configuration"

if [[ ! -f "$ENV_FILE" ]]; then
  warn ".env file not found. Creating a template..."
  cat > "$ENV_FILE" <<'EOF'
# ─── WebVuln-AI Environment Configuration ────────────────────────────────────
# Get your key at: https://console.anthropic.com/
ANTHROPIC_API_KEY=your_api_key_here

# MCP Server settings
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8765

# Flask settings
FLASK_PORT=5000
FLASK_DEBUG=true
EOF
  warn "Please edit .env and add your ANTHROPIC_API_KEY, then re-run this script."
  exit 1
fi

# Load .env
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ "${ANTHROPIC_API_KEY:-}" == "your_api_key_here" ]] || [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  error "ANTHROPIC_API_KEY is not set in .env. Please add your key and retry."
fi

log ".env loaded successfully"
log "API key: ${ANTHROPIC_API_KEY:0:10}...${ANTHROPIC_API_KEY: -4}"

# ── Step 3: Clone / update dataset ───────────────────────────────────────────
header "Step 3: Vulnerability dataset"

if [[ -d "$DATA_DIR/.git" ]]; then
  info "Dataset already cloned. Pulling latest changes..."
  git -C "$DATA_DIR" pull --ff-only && log "Dataset updated" || warn "Could not update dataset (continuing with existing)"
elif [[ -d "$DATA_DIR" ]] && [[ "$(ls -A "$DATA_DIR")" ]]; then
  warn "data/vulnerabilities/ exists but is not a git repo. Using existing files."
else
  info "Cloning WebVuln--Plus dataset..."
  mkdir -p "$(dirname "$DATA_DIR")"
  git clone "$DATASET_REPO" "$DATA_DIR" && log "Dataset cloned to $DATA_DIR"
fi

VULN_COUNT=$(find "$DATA_DIR" -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
log "Found $VULN_COUNT vulnerability data files"

# ── Step 4: Python virtual environment ───────────────────────────────────────
header "Step 4: Python virtual environment"

if [[ ! -d "$VENV_DIR" ]]; then
  info "Creating virtual environment in $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
  log "Virtual environment created"
else
  log "Virtual environment already exists"
fi

# Activate
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
log "Virtual environment activated"

# ── Step 5: Install dependencies ─────────────────────────────────────────────
header "Step 5: Installing dependencies"

if [[ ! -f "$REQUIREMENTS" ]]; then
  warn "requirements.txt not found. Creating a default one..."
  cat > "$REQUIREMENTS" <<'EOF'
# WebVuln-AI Requirements
flask>=3.0.0
anthropic>=0.25.0
mcp>=1.0.0
pyyaml>=6.0.1
python-dotenv>=1.0.0
requests>=2.31.0
aiohttp>=3.9.0
asyncio-mqtt>=0.16.0
EOF
  log "Created default requirements.txt"
fi

pip install --upgrade pip -q
pip install -r "$REQUIREMENTS" -q
log "All dependencies installed"

# ── Step 6: Validate project structure ───────────────────────────────────────
header "Step 6: Validating project structure"

MISSING=0
for f in "mcp_server/server.py" "mcp_server/vuln_loader.py" "mcp_server/tools.py" \
          "ai_agent/tutor_agent.py" "web/app.py"; do
  if [[ -f "$f" ]]; then
    log "Found $f"
  else
    warn "Missing $f (will need to be created)"
    MISSING=$((MISSING + 1))
  fi
done

if [[ "$MISSING" -gt 0 ]]; then
  warn "$MISSING file(s) are missing — some components may not start."
fi

# ── Step 7: Start MCP Server ──────────────────────────────────────────────────
header "Step 7: Starting MCP server"

if [[ -f "mcp_server/server.py" ]]; then
  info "Launching MCP server on $MCP_HOST:$MCP_PORT..."
  python3 mcp_server/server.py &
  MCP_PID=$!
  sleep 2

  if kill -0 "$MCP_PID" 2>/dev/null; then
    log "MCP server running (PID $MCP_PID)"
  else
    error "MCP server failed to start. Check mcp_server/server.py"
  fi
else
  warn "mcp_server/server.py not found — skipping MCP server startup"
fi

# ── Step 8: Start Flask Web App ───────────────────────────────────────────────
header "Step 8: Starting Flask web app"

if [[ -f "web/app.py" ]]; then
  info "Launching Flask app on http://localhost:$FLASK_PORT..."
  FLASK_APP=web/app.py python3 -m flask run --host=0.0.0.0 --port="$FLASK_PORT" &
  FLASK_PID=$!
  sleep 2

  if kill -0 "$FLASK_PID" 2>/dev/null; then
    log "Flask app running (PID $FLASK_PID)"
  else
    error "Flask app failed to start. Check web/app.py"
  fi
else
  warn "web/app.py not found — skipping Flask startup"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  🛡️  WebVuln-AI is running!${NC}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════════════${NC}"
echo ""
echo -e "  🌐  Web UI  →  ${BOLD}http://localhost:$FLASK_PORT${NC}"
echo -e "  🔌  MCP     →  ${BOLD}$MCP_HOST:$MCP_PORT${NC}"
echo -e "  📂  Dataset →  ${BOLD}$DATA_DIR${NC}"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${NC} to stop all services."
echo ""

# Wait for background processes
wait