"""
One-time seed for the questions table from Phase 4's merged question bank —
needed before /exam/mcq/submit (M1) has anything real to look up by
question_id. questions was never populated by an earlier phase.

Run: cd backend && ~/.venvs/mentora-backend/bin/python scripts/seed_questions.py
"""

import ast
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.models import Question
from database.session import Base, SessionLocal, engine

CSV_PATH = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m1" / "question_bank_final.csv"


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Question).count() > 0:
            print("questions table already has rows — skipping (delete rows first to re-seed).")
            return

        added = 0
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if not row.get("question_text") or not row.get("topic"):
                    continue
                try:
                    options = ast.literal_eval(row["options"]) if row["options"] else {}
                except (ValueError, SyntaxError):
                    options = {}
                db.add(Question(
                    question_id=int(row["question_id"]),
                    subject=row["subject"] or "",
                    topic=row["topic"],
                    subtopic=row.get("subtopic") or None,
                    difficulty=row.get("difficulty") or "medium",
                    question_text=row["question_text"],
                    options=options,
                    correct_answer=row.get("correct_answer") or "",
                    source=row.get("source") or None,
                ))
                added += 1
        db.commit()
        print(f"Seeded {added} questions rows.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
