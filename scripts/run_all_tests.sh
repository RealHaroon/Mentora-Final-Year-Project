#!/bin/bash
# Phase 8 §10 — regression safety net. Run this before every significant
# change from here on.
#
# Deviates from the doc's sketch: no frontend Playwright step. The Next.js
# frontend isn't wired to this backend at all yet (confirmed in Phase 6 — no
# fetch/axios calls to /api/exam|career|dashboard anywhere in frontend/), so
# there is no real frontend-backend integration for Playwright to test
# against. Add that step back here once Phase 2's actual wiring is done.
set -e

cd "$(dirname "$0")/.."

echo "Backend unit + integration tests..."
cd backend && ~/.venvs/mentora-backend/bin/python -m pytest tests/ -v
cd ..

echo "All tests passed."
