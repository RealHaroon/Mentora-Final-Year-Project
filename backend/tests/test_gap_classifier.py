import json

from config import settings
from ml_core.models.gap_classifier import GapClassifier


def test_gap_classifier_known_example():
    with open(settings.topics_json) as f:
        topics = json.load(f)
    clf = GapClassifier(model_dir=settings.model1_path, topics=topics)
    clf.load()
    result = clf.infer("The equation $ax^2 + bx + c = 0$ has coefficients that satisfy...")
    assert "Algebra" in result
