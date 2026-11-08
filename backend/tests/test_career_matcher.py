from config import settings
from ml_core.models.career_matcher import CareerMatcher

_CATALOGUE = [
    {"career_id": 1, "title": "Data Scientist", "text": "Data Scientist: Python, Statistics, Machine Learning, Deep Learning, TensorFlow, SQL."},
    {"career_id": 4, "title": "Software Engineer", "text": "Software Engineer: Python, System Design, APIs, Data Structures, Algorithms."},
]


def test_career_matcher_ranks_closest_skill_set_first():
    matcher = CareerMatcher(model_path=settings.model4_path, career_catalogue=_CATALOGUE)
    matcher.load()
    result = matcher.infer("Python, TensorFlow, deep learning, statistics", top_k=2)
    assert result[0]["career_title"] == "Data Scientist"
    assert 0 <= result[0]["match_score"] <= 100
