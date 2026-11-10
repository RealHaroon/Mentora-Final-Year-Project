#!/bin/bash
# Phase 9 §1.3 — the one-click entry point. Run preflight_check.py first
# (or just let this script's own port/env checks catch the obvious cases).
#
# Adapted from the doc's sketch: no Ollama step (Groq is cloud, nothing
# local to launch — see Phase 7's header note). Starts backend only for
# now — frontend start is commented out below since it has no real
# wiring to the backend yet; uncomment once that's done.
set -e
cd "$(dirname "$0")/.."

echo "Launching MENTORA..."
echo "Running preflight checks..."
cd backend && ~/.venvs/mentora-backend/bin/python ../scripts/preflight_check.py
cd ..

./scripts/start_backend.sh &
BACKEND_PID=$!
echo "Backend starting (pid $BACKEND_PID), waiting for it to come up..."
sleep 5

# Uncomment once the frontend is actually wired to this backend:
# ./scripts/start_frontend.sh &
# sleep 5
# open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null

echo "Backend is up at http://localhost:8000 (Swagger docs: http://localhost:8000/docs)"
open http://localhost:8000/docs 2>/dev/null || xdg-open http://localhost:8000/docs 2>/dev/null || true

wait $BACKEND_PID
