"""
One-time seed for career_profiles — needed before CareerMatcher (M4) has
anything to rank against. career_profiles was never populated by an earlier
phase; this fills it with the same 5 careers the Phase 2 mock used in
routers/career.py, so the real model's output stays comparable to what the
frontend already expects.

Run: cd backend && ~/.venvs/mentora-backend/bin/python scripts/seed_careers.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.models import CareerProfile
from database.session import Base, SessionLocal, engine

CAREERS = [
    {
        "career_id": 1,
        "title": "Data Scientist",
        "description": "Analyzes large datasets to extract insights and build predictive models.",
        "required_skills": ["Python", "Statistics", "Machine Learning", "Deep Learning", "TensorFlow", "SQL"],
        "category": "Technology",
    },
    {
        "career_id": 2,
        "title": "ML Engineer",
        "description": "Builds and deploys machine learning systems and pipelines in production.",
        "required_skills": ["Python", "TensorFlow", "PyTorch", "MLOps", "Docker", "System Design"],
        "category": "Technology",
    },
    {
        "career_id": 3,
        "title": "Business Analyst",
        "description": "Bridges business needs and data, using analytics to support decisions.",
        "required_skills": ["SQL", "Tableau", "Excel", "Data Analysis", "Communication"],
        "category": "Business",
    },
    {
        "career_id": 4,
        "title": "Software Engineer",
        "description": "Designs, builds, and maintains software systems and APIs.",
        "required_skills": ["Python", "System Design", "APIs", "Data Structures", "Algorithms"],
        "category": "Technology",
    },
    {
        "career_id": 5,
        "title": "Product Manager",
        "description": "Defines product strategy and leads cross-functional teams to ship features.",
        "required_skills": ["Leadership", "Strategy", "UX", "Communication", "Roadmapping"],
        "category": "Business",
    },
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = {c.career_id for c in db.query(CareerProfile).all()}
        added = 0
        for c in CAREERS:
            if c["career_id"] in existing:
                continue
            db.add(CareerProfile(**c))
            added += 1
        db.commit()
        print(f"Seeded {added} career_profiles rows ({len(existing)} already present).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
