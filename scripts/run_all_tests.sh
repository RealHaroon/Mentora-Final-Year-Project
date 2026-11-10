#!/bin/bash
# Phase 8 §10 — regression safety net. Run this before every significant
# change from here on.
#
# Deviates from the doc's sketch: no frontend Playwright step. Not because
# the frontend is unwired — it was wired back in Phase 2, a claim otherwise
# got this wrong across Phases 6-9 (see docs/phase10/drift_check.md) — but
# because no Playwright suite has actually been written yet. That's
# genuinely still open work, not blocked on anything.
set -e

cd "$(dirname "$0")/.."

echo "Backend unit + integration tests..."
cd backend && ~/.venvs/mentora-backend/bin/python -m pytest tests/ -v
cd ..

echo "All tests passed."
