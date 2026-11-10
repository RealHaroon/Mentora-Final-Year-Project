#!/bin/bash
# Phase 9 §1 — one-click backend startup. No Ollama step here, unlike the
# doc's original sketch: Phase 7 switched generation to Groq (cloud), so
# there's no local LLM service to launch.
set -e
cd "$(dirname "$0")/../backend"

# This machine's venv lives at ~/.venvs/mentora-backend (see README.md for
# how to recreate it from requirements.txt on a fresh machine) — fall back
# to a project-local backend/venv/ or plain python3 if that's not found.
if [ -x "$HOME/.venvs/mentora-backend/bin/python" ]; then
    PYTHON="$HOME/.venvs/mentora-backend/bin/python"
elif [ -x "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

echo "Starting FastAPI backend on port 8000 (using $PYTHON)..."
exec "$PYTHON" -m uvicorn main:app --port 8000
