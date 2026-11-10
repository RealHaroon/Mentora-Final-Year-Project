#!/bin/bash
# Phase 9 §1.3 — the one-click entry point. Run preflight_check.py first
# (or just let this script's own port/env checks catch the obvious cases).
#
# Adapted from the doc's sketch: no Ollama step (Groq is cloud, nothing
# local to launch — see Phase 7's header note). Started backend-only from
# Phase 9 through 2026-11-10 on the mistaken belief that the frontend had
# no real wiring — it did (Phase 2), just against response shapes Phases
# 6-7 later changed. A 2026-11-10 audit fixed that drift; starting the
# frontend here is no longer misleading. See docs/phase10/drift_check.md.
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

./scripts/start_frontend.sh &
FRONTEND_PID=$!
echo "Frontend starting (pid $FRONTEND_PID), waiting for it to come up..."
sleep 5
open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || true

echo "Backend is up at http://localhost:8000 (Swagger docs: http://localhost:8000/docs)"
echo "Frontend is up at http://localhost:3000"

wait $BACKEND_PID $FRONTEND_PID
