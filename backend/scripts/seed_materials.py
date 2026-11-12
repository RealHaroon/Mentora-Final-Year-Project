"""
One-time seed for the shared course-material catalogue (materials rows with
owner_user_id=NULL) — the same 3 board/official resources the old Phase 2
mock in routers/learning.py hardcoded, now visible to every real student
instead of being a shared in-memory list. A student's own uploads get a
real owner_user_id and stay private; this script never touches those.

Run: cd backend && ~/.venvs/mentora-backend/bin/python scripts/seed_materials.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.models import Material
from database.session import Base, SessionLocal, engine

CATALOGUE = [
    {"title": "MDCAT Biology Full Syllabus 2025", "size_label": "4.2 MB", "source": "Sindh Board"},
    {"title": "Mathematics Chapter Notes — Entry Test", "size_label": "1.8 MB", "source": "Self-uploaded"},
    {"title": "CSS Past Papers 2020-2024", "size_label": "6.1 MB", "source": "FPSC Official PDFs"},
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_titles = {
            m.title for m in db.query(Material).filter(Material.owner_user_id.is_(None)).all()
        }
        added = 0
        for item in CATALOGUE:
            if item["title"] in existing_titles:
                continue
            db.add(Material(owner_user_id=None, **item))
            added += 1
        db.commit()
        print(f"Seeded {added} catalogue materials rows ({len(existing_titles)} already present).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
