#!/usr/bin/env bash
# =============================================================================
# run.sh — WebVuln-AI Setup & Launch Script
# Fully local — powered by Ollama (no API key required)
# =============================================================================

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ── Config ────────────────────────────────────────────────────────────────────
VENV_DIR="      .venv"
DATA_DIR="data/vulnerabilities"
DATASET_REPO="https://github.com/mngugi/WebVuln--Plus"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2}"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
FLASK_PORT="${FLASK_PORT:-5000}"
REQUIREMENTS="requirements.txt"
ENV_FILE=".env"

# ── Helpers ───────────────────────────────────────────────────────────────────
log()    { echo -e "${GREEN}[✔]${NC} $1"; }
info()   { echo -e "${BLUE}[→]${NC} $1"; }
warn()   { echo -e "${YELLOW}[!]${NC} $1"; }
error()  { echo -e "${RED}[✘]${NC} $1"; exit 1; }
header() { echo -e "\n${BOLD}${BLUE}$1${NC}\n"; }

cleanup() {
  header "Shutting down..."
  [[ -n "${FLASK_PID:-}" ]] && kill "$FLASK_PID" 2>/dev/null && log "Flask stopped"
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
echo "         🛡️  WebVuln-AI — Powered by Ollama (100% Local)"
echo -e "${NC}"

# ── Step 1: Check prerequisites ───────────────────────────────────────────────
header "Step 1: Checking prerequisites"

command -v python3 >/dev/null 2>&1 || error "python3 not installed"
command -v pip3    >/dev/null 2>&1 || error "pip3 not installed"
command -v git     >/dev/null 2>&1 || error "git not installed"

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log "Python $PYTHON_VERSION detected"

# ── Step 2: Check Ollama ──────────────────────────────────────────────────────
header "Step 2: Checking Ollama"

if ! command -v ollama >/dev/null 2>&1; then
  warn "Ollama not found. Installing..."
  curl -fsSL https://ollama.com/install.sh | sh
  log "Ollama installed"
else
  log "Ollama found: $(ollama --version 2>/dev/null || echo 'installed')"
fi

# Start Ollama serve in background if not running
if ! curl -s "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  info "Starting Ollama server..."
  ollama serve &>/tmp/ollama.log &
  OLLAMA_SERVER_PID=$!
  sleep 3
  log "Ollama server started (PID $OLLAMA_SERVER_PID)"
else
  log "Ollama server already running at $OLLAMA_URL"
fi

# Check if model is pulled
info "Checking for model '$OLLAMA_MODEL'..."
if ! ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
  info "Pulling model '$OLLAMA_MODEL' (this may take a few minutes)..."
  ollama pull "$OLLAMA_MODEL" && log "Model '$OLLAMA_MODEL' ready"
else
  log "Model '$OLLAMA_MODEL' already available"
fi

# ── Step 3: Clone / update dataset ───────────────────────────────────────────
header "Step 3: Vulnerability dataset"

if [[ -d "$DATA_DIR/.git" ]]; then
  info "Dataset found. Pulling latest..."
  git -C "$DATA_DIR" pull --ff-only && log "Dataset updated" || warn "Could not update (using existing)"
elif [[ -d "$DATA_DIR" ]] && [[ "$(ls -A "$DATA_DIR")" ]]; then
  warn "data/vulnerabilities/ exists but is not a git repo. Using as-is."
else
  info "Cloning WebVuln--Plus dataset..."
  mkdir -p "$(dirname "$DATA_DIR")"
  git clone "$DATASET_REPO" "$DATA_DIR" && log "Dataset cloned to $DATA_DIR"
fi

VULN_COUNT=$(find "$DATA_DIR" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
log "Found $VULN_COUNT markdown files in dataset"

# ── Step 4: Python virtual environment ───────────────────────────────────────
header "Step 4: Python virtual environment"

VENV_DIR=".venv"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR" && log "Virtual environment created"
else
  log "Virtual environment already exists"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
log "Virtual environment activated"

# ── Step 5: Install dependencies ─────────────────────────────────────────────
header "Step 5: Installing dependencies"

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
    warn "Missing $f"
    MISSING=$((MISSING + 1))
  fi
done
[[ "$MISSING" -gt 0 ]] && warn "$MISSING file(s) missing — some components may not start"

# ── Step 7: Write .env ────────────────────────────────────────────────────────
header "Step 7: Environment config"

if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<EOF
# WebVuln-AI — Ollama configuration (no API key needed!)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
FLASK_PORT=5000
FLASK_DEBUG=true
EOF
  log ".env created"
else
  log ".env already exists"
fi

# Load .env
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# ── Step 8: Start Flask Web App ───────────────────────────────────────────────
header "Step 8: Starting Flask web app"

if [[ -f "web/app.py" ]]; then
  info "Launching Flask app on http://localhost:$FLASK_PORT..."
  FLASK_APP=web.app python3 -m flask run --host=0.0.0.0 --port="$FLASK_PORT" &
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
echo -e "  🌐  Web UI   →  ${BOLD}http://localhost:$FLASK_PORT${NC}"
echo -e "  🤖  Model    →  ${BOLD}$OLLAMA_MODEL${NC}"
echo -e "  🔌  Ollama   →  ${BOLD}$OLLAMA_URL${NC}"
echo -e "  📂  Dataset  →  ${BOLD}$DATA_DIR${NC}"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${NC} to stop."
echo ""

wait