"""
Phase 9 §2 — ONE deliberately-designed demo account, not random Faker data
(Phase 8's seed_test_data.py is for load testing, not demos). Every value
here is chosen to tell a clear, coherent story on screen:
- a clearly weak topic (Algebra) for the gap-classifier/weak-topics demo
- a clean, consistently improving score trend for the trajectory-predictor
  ("at-risk check") demo
- a real CV run through the ACTUAL M5 model (not hand-faked output) that
  produces a clean, legible skill list for the career-ranking demo

Idempotent: re-running this deletes and recreates the demo account, so it's
safe to run again after a bad rehearsal without manual cleanup.

Run: cd backend && ~/.venvs/mentora-backend/bin/python scripts/seed_demo_account.py
"""

import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.models import (
    CvUpload,
    ExamSession,
    PlaylistItem,
    StudentIntelligenceProfile,
    TopicScore,
    User,
    WatchHistoryEntry,
    utcnow,
)
from database.session import Base, SessionLocal, engine
from ml_core.models.cv_ner import CVNerExtractor
from config import settings
from routers.learning import _youtube_search_url
from services.auth_service import hash_password

# Same 3 videos the old Phase 2 mock hardcoded for every account — now a
# real per-user seed instead of shared in-memory state (see routers/learning.py).
DEMO_PLAYLIST = [
    {"title": "Quadratic Equations — Full Chapter", "subject": "Mathematics", "source": "MathCity.org", "duration_min": 18, "note": "AI-added from today's session"},
    {"title": "Grammar Tenses — Active & Passive Voice", "subject": "English", "source": "Khan Academy", "duration_min": 12, "note": "AI-added"},
    {"title": "Geometry — Circles & Angles Full Revision", "subject": "Mathematics", "source": "MathCity.org", "duration_min": 24, "note": "AI-added"},
]

# 14 watch-history entries within the last week, matching the old mock's
# hardcoded "14 watched this week" stat — now a real, computed count.
DEMO_WATCH_HISTORY = [
    ("Quadratic Equations — Full Chapter", "Mathematics"),
    ("Grammar Tenses — Active & Passive Voice", "English"),
    ("Geometry — Circles & Angles Full Revision", "Mathematics"),
    ("Algebra Basics — Worked Examples", "Mathematics"),
    ("Advanced Math — Functions Overview", "Mathematics"),
    ("Grammar Tenses — Active & Passive Voice", "English"),
    ("Geometry — Circles & Angles Full Revision", "Mathematics"),
    ("Quadratic Equations — Full Chapter", "Mathematics"),
    ("Problem Solving Strategies", "Mathematics"),
    ("Data Analysis Fundamentals", "Mathematics"),
    ("Algebra Basics — Worked Examples", "Mathematics"),
    ("Grammar Tenses — Active & Passive Voice", "English"),
    ("Advanced Math — Functions Overview", "Mathematics"),
    ("Geometry — Circles & Angles Full Revision", "Mathematics"),
]

DEMO_EMAIL = "demo@mentora.pk"
DEMO_PASSWORD = "MentoraDemo2026!"
CV_PATH = Path(__file__).resolve().parent / "demo_assets" / "demo_student_cv.txt"

# Last 5 total_score values, oldest first. M3's /dashboard/at-risk-check
# reads exactly the last 5 ExamSession rows by start_time.
#
# NOT a hand-constructed monotonic trend, by design — tested 10 monotonic
# sequences against the REAL model before picking this (see git history /
# session notes): 9/10 predicted the OPPOSITE direction from the visible
# trend (every ascending sequence tested -> "declining", every descending
# one -> "improving"). Consistent with M3's already-documented noise-floor
# training data (scripts/phase5/README.md) — a model trained on data with
# no real persistent trend learns mean-reversion as its best next-step
# strategy, which looks "backwards" on any artificially monotonic demo
# sequence. A small-variation, no-clear-trend sequence like this one
# reliably predicts "stable" with a plausible next value — verified
# against the real model, not assumed — and doesn't visually contradict
# its own verdict the way a monotonic one would.
SCORE_HISTORY = [58, 61, 59, 62, 60]

# One clearly weak topic (low score, triggers the "Needs urgent review" note
# in /dashboard/weak-topics) and two healthy ones for contrast.
TOPIC_SCORES = [
    ("Mathematics", "Algebra", 32.0),
    ("English", "General English", 71.0),
    ("Mathematics", "Geometry and Trigonometry", 78.0),
]


def extract_real_cv_skills() -> dict:
    # Genuinely run the CV through M5, not hand-written output — same
    # principle as the Phase 9 doc's demo-cache guidance: cached/curated
    # demo data must still be real model output, not fabricated.
    id2tag = {int(k): v for k, v in json.load(open(settings.m5_id2tag_json)).items()}
    extractor = CVNerExtractor(model_dir=settings.model5_path, id2tag=id2tag)
    extractor.load()
    return extractor.infer(CV_PATH.read_text())


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing is not None:
            print(f"Removing existing demo account (user_id={existing.user_id}) for a clean re-seed...")
            db.delete(existing)
            db.commit()

        user = User(
            first_name="Ayesha", last_name="Memon", email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            university="University of Sindh, Laar Campus", exam_goal="sindh_university",
        )
        db.add(user)
        db.flush()
        db.add(StudentIntelligenceProfile(user_id=user.user_id))

        for score in SCORE_HISTORY:
            db.add(ExamSession(
                user_id=user.user_id, exam_type="mcq_practice", subject="Mixed",
                start_time=utcnow(), total_score=float(score),
            ))

        for subject, topic, score in TOPIC_SCORES:
            db.add(TopicScore(user_id=user.user_id, subject=subject, topic=topic, score=score))

        for video in DEMO_PLAYLIST:
            db.add(PlaylistItem(
                user_id=user.user_id, video_url=_youtube_search_url(video["title"], video["source"]), **video,
            ))

        for i, (title, subject) in enumerate(DEMO_WATCH_HISTORY):
            db.add(WatchHistoryEntry(
                user_id=user.user_id, title=title, subject=subject,
                watched_at=utcnow() - timedelta(days=i % 6, hours=i),
            ))

        print("Extracting CV skills via the real M5 model...")
        extracted = extract_real_cv_skills()
        print("Extracted:", extracted)

        gpa_raw = extracted.get("gpa")
        try:
            gpa = float(gpa_raw) if gpa_raw else None
        except ValueError:
            gpa = None

        db.add(CvUpload(
            user_id=user.user_id, file_path=str(CV_PATH),
            extracted_skills=extracted["skills"], gpa=gpa,
            certifications=extracted["certifications"], projects=extracted.get("degrees", []),
        ))

        db.commit()
        print(f"\nDemo account ready: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print("Call /career/rankings once after this to populate career_rankings "
              "(needs the live CareerMatcher model, not done here to keep this script fast).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
