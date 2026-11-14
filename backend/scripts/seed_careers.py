"""
One-time seed for career_profiles — needed before CareerMatcher (M4) has
anything to rank against. career_profiles was never populated by an earlier
phase; this fills it with the same 5 careers the Phase 2 mock used in
routers/career.py, so the real model's output stays comparable to what the
frontend already expects.

2026-11-14 — added 5 more (ids 6-10) after a user noted there were only
5-6 careers to pick from. Each new one has a matching RAG content file in
rag_pipelines/career_rag/content/ (re-run that directory's ingest.py after
adding here) and a CareerGoal enum entry (schemas/career.py +
routers/interview.py's _CAREER_GOAL_IDS + the frontend's
CAREER_ID_TO_GOAL/dropdown in app/career/page.tsx) so they're reachable
from the roadmap-view and mock-interview dropdown, not just the ranking
list. required_skills drives the auto-generated roadmap (see
routers/career.py's get_roadmap) — there's no separate roadmap table to
hand-author.

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
    {
        "career_id": 6,
        "title": "UX/UI Designer",
        "description": "Researches user needs and designs usable, visually consistent product interfaces.",
        "required_skills": ["Figma", "User Research", "Wireframing", "Prototyping", "Design Systems", "Communication"],
        "category": "Design",
    },
    {
        "career_id": 7,
        "title": "DevOps Engineer",
        "description": "Builds and maintains the deployment pipelines and infrastructure other engineers ship on.",
        "required_skills": ["Linux", "Docker", "Kubernetes", "CI/CD", "Cloud (AWS/Azure)", "Scripting"],
        "category": "Technology",
    },
    {
        "career_id": 8,
        "title": "Cybersecurity Analyst",
        "description": "Monitors systems and networks for threats and helps close security gaps before they're exploited.",
        "required_skills": ["Networking", "Linux", "SIEM Tools", "Threat Analysis", "Penetration Testing", "Security Fundamentals"],
        "category": "Technology",
    },
    {
        "career_id": 9,
        "title": "Digital Marketing Specialist",
        "description": "Plans and runs online campaigns and measures what actually drives real results.",
        "required_skills": ["SEO", "Content Strategy", "Google Analytics", "Social Media Marketing", "Copywriting", "A/B Testing"],
        "category": "Business",
    },
    {
        "career_id": 10,
        "title": "Financial Analyst",
        "description": "Evaluates financial data and forecasts to support budgeting and investment decisions.",
        "required_skills": ["Excel", "Financial Modeling", "Accounting Fundamentals", "Valuation", "Data Analysis", "Communication"],
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
