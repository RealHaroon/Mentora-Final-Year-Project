"""
Phase 8 §9 — realistic data volume. Everything tested so far has used 1-2
accounts; this seeds a more realistic volume (default 50 students, 15 exam
sessions each) and is used to re-check /dashboard and /career assumptions
baked in during Phase 2's mock-data wiring (e.g. "exactly 10 sessions").

This writes to the REAL dev database (settings.database_url), same as
seed_careers.py/seed_questions.py — run those two first if not already done.

Run: cd backend && ~/.venvs/mentora-backend/bin/python scripts/seed_test_data.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faker import Faker

from database.models import ExamSession, StudentIntelligenceProfile, TopicScore, User, utcnow
from database.session import Base, SessionLocal, engine
from services.auth_service import hash_password

fake = Faker()

TOPICS = [
    ("Mathematics", "Algebra"), ("Mathematics", "Geometry and Trigonometry"),
    ("English", "General English"), ("Logical Reasoning", "General Logical Reasoning"),
    ("Physics", "General Physics"), ("Biology", "General Biology"), ("Chemistry", "General Chemistry"),
]


def seed(n_students=50, sessions_per_student=15):
    db = SessionLocal()
    try:
        created_users = 0
        for _ in range(n_students):
            email = fake.unique.email()
            if db.query(User).filter(User.email == email).first():
                continue
            user = User(
                first_name=fake.first_name(), last_name=fake.last_name(), email=email,
                password_hash=hash_password("testpass123"), university="University of Sindh, Laar Campus",
                exam_goal=random.choice(["sindh_university", "mehran_university", "lumhs"]),
            )
            db.add(user)
            db.flush()
            db.add(StudentIntelligenceProfile(user_id=user.user_id))
            created_users += 1

            base_score = random.randint(40, 70)
            for i in range(sessions_per_student):
                # a mild upward drift, not pure randomness, so score-trend
                # charts have something resembling a real trend line to render
                score = max(0, min(100, base_score + i * random.uniform(-1, 2)))
                subject, _ = random.choice(TOPICS)
                db.add(ExamSession(
                    user_id=user.user_id, exam_type="mcq_practice", subject=subject,
                    start_time=utcnow(), total_score=round(score, 1),
                ))

            for subject, topic in random.sample(TOPICS, k=random.randint(2, 4)):
                db.add(TopicScore(user_id=user.user_id, subject=subject, topic=topic, score=random.uniform(20, 95)))

        db.commit()
        print(f"Seeded {created_users} new students, ~{created_users * sessions_per_student} exam sessions.")
    finally:
        db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed()
