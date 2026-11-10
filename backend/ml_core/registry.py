"""Builds the ModelManager's registry — the one place that knows every
model's file path and runtime config, called once at app startup."""

import json

from config import settings
from database.models import CareerProfile
from database.session import SessionLocal
from ml_core.models.career_matcher import CareerMatcher
from ml_core.models.cv_ner import CVNerExtractor
from ml_core.models.gap_classifier import GapClassifier
from ml_core.models.question_generator import QuestionGenerator
from ml_core.models.trajectory_predictor import TrajectoryPredictor


def _load_career_catalogue() -> list[dict]:
    # career_profiles is the single source of truth for career data (used by
    # /career/rankings, /career/roadmap, etc. too) — read it directly rather
    # than maintaining a second, easily-stale JSON copy of the same catalogue.
    # Needs rows seeded (see scripts/seed_careers.py) before this returns anything.
    db = SessionLocal()
    try:
        rows = db.query(CareerProfile).all()
        return [
            {
                "career_id": row.career_id,
                "title": row.title,
                "text": f"{row.title}: {', '.join(row.required_skills or [])}. {row.description or ''}".strip(),
            }
            for row in rows
        ]
    finally:
        db.close()


def build_model_registry() -> dict:
    with open(settings.topics_json) as f:
        topics = json.load(f)  # the same topic list used to build M1's labels in Phase 4
    with open(settings.m5_id2tag_json) as f:
        id2tag = {int(k): v for k, v in json.load(f).items()}

    return {
        "trajectory_predictor": TrajectoryPredictor(settings.model3_path),
        "career_matcher": CareerMatcher(settings.model4_path, _load_career_catalogue()),
        "gap_classifier": GapClassifier(settings.model1_path, topics),
        "cv_ner": CVNerExtractor(settings.model5_path, id2tag),
        "question_generator": QuestionGenerator(settings.model2_path),
    }
