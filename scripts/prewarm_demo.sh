#!/bin/bash
# Phase 9 §3.1 — pre-warm every on-demand model before a demo/rehearsal, so
# the Model Manager's lazy-loading (Phase 6) doesn't eat into your live
# demo time. Run this 2-3 minutes before starting, not the moment before —
# M2 in particular can take real time to load + run its retries.
#
# No Ollama pre-warm step, unlike the doc's sketch — Groq has no local
# load time to hide (Phase 7).
set -e

BASE_URL="${1:-http://localhost:8000}"
EMAIL="demo@mentora.pk"
PASSWORD="MentoraDemo2026!"

echo "Logging in as the demo account..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
    echo "Could not log in as the demo account — run scripts/seed_demo_account.py first."
    exit 1
fi
AUTH="Authorization: Bearer $TOKEN"

echo "Pre-warming M1 (gap classifier)..."
curl -s -X POST "$BASE_URL/exam/mcq/submit" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"question_id":"1778","answer":"A"}' > /dev/null

echo "Pre-warming M2 (question generator) — this one's slow, be patient..."
curl -s "$BASE_URL/exam/mcq?topic=Algebra" -H "$AUTH" > /dev/null

echo "Pre-warming M5 (CV NER)..."
curl -s -X POST "$BASE_URL/career/cv-upload" -H "$AUTH" \
    -F "cv_file=@backend/scripts/demo_assets/demo_student_cv.txt;type=text/plain" > /dev/null

echo "Warming up the RAG endpoints (Groq) too — a slow/cold first call here is as visible as a slow model load..."
curl -s "$BASE_URL/exam/topic-explainer" -H "$AUTH" --get --data-urlencode "query=how do I solve a quadratic equation" > /dev/null
curl -s "$BASE_URL/career/ask" -H "$AUTH" --get --data-urlencode "query=what skills do I need to become a data scientist" > /dev/null

echo "All models pre-warmed."
