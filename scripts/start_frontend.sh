#!/bin/bash
# Phase 9 §1 — frontend startup. NOTE: as of Phase 8, the frontend has no
# real wiring to the backend yet (no fetch/axios calls anywhere) — this
# starts a working Next.js app showing Phase 2's hardcoded mock data, not
# a connected demo. Useful once frontend wiring is done; not yet part of
# a real end-to-end demo.
set -e
cd "$(dirname "$0")/../frontend"
echo "Starting Next.js frontend on port 3000..."
exec npm run dev
