#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [[ ! -x "$BACKEND_DIR/.venv/bin/uvicorn" ]]; then
  echo "Backend virtualenv is missing dependencies."
  echo "Run: cd backend && python3 -m venv .venv && .venv/bin/pip install -e \".[dev]\""
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Frontend dependencies are missing."
  echo "Run: cd frontend && npm install"
  exit 1
fi

cleanup() {
  echo
  echo "Stopping local services..."
  jobs -p | xargs -r kill 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "Starting backend on http://127.0.0.1:8000"
(
  cd "$BACKEND_DIR"
  .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &

echo "Starting frontend on http://localhost:3000"
(
  cd "$FRONTEND_DIR"
  npm run dev
) &

wait
