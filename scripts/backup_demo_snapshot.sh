#!/bin/bash
# Phase 9 §6 — run this right after seeding + verifying the demo account
# (scripts/seed_demo_account.py). If anything gets corrupted during
# rehearsal, restoring this snapshot is a two-minute fix instead of a
# re-seed-and-re-verify scramble.
set -e
cd "$(dirname "$0")/.."

mkdir -p backups
STAMP=$(date +%Y%m%d_%H%M%S)
cp backend/mentora.db "backups/demo_snapshot_${STAMP}.db"
echo "Snapshot saved: backups/demo_snapshot_${STAMP}.db"
echo "To restore: cp backups/demo_snapshot_${STAMP}.db backend/mentora.db"
