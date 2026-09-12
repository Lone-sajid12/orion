#!/usr/bin/env bash
# ORION launcher — starts the API engine + web interface.
# Usage:  ./start.sh            (development: backend :8000 + frontend :5173)
#         ./start.sh --single   (production: build frontend once, serve everything from :8000)
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-dev}"

check_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "ORION needs '$1' installed. See README."; exit 1; }; }
check_cmd python3
[ "$MODE" = "--single" ] || check_cmd npm

if [ ! -d backend/.venv-state ] && [ ! -f backend/.deps-ok ]; then
  echo "▸ Installing Python dependencies (one-time)…"
  python3 -m pip install -r backend/requirements.txt
  touch backend/.deps-ok
fi

if [ "$MODE" = "--single" ]; then
  check_cmd npm
  echo "▸ Building frontend…"
  (cd frontend && npm install --silent && npm run build --silent)
  echo "▸ ORION running at  http://localhost:8000   (single-process production mode)"
  (cd backend && python3 -m uvicorn app:app --host 127.0.0.1 --port 8000)
else
  if [ ! -d frontend/node_modules ]; then
    echo "▸ Installing frontend dependencies (one-time)…"
    (cd frontend && npm install)
  fi
  echo "▸ Starting ORION engine  → http://localhost:8000"
  echo "▸ Starting ORION interface → http://localhost:5173"
  echo "  (Ctrl+C stops both)"
  trap 'kill 0' EXIT
  (cd backend && python3 -m uvicorn app:app --host 127.0.0.1 --port 8000) &
  (cd frontend && npm run dev) &
  wait
fi
