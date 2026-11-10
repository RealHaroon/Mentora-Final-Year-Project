#!/bin/bash
# Phase 9 §1 — frontend startup. Wired to the real backend since Phase 2;
# Phases 8-9's "no real wiring" note here was wrong — see
# docs/phase10/drift_check.md. Requires the backend running first
# (NEXT_PUBLIC_API_URL in frontend/.env.local points at it).
set -e
cd "$(dirname "$0")/../frontend"
echo "Starting Next.js frontend on port 3000..."
exec npm run dev
