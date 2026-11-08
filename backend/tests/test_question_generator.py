from config import settings
from ml_core.models.question_generator import QuestionGenerator


def test_question_generator_either_returns_valid_json_or_raises():
    # M2 is a known-weak model (Phase 5's parity check: 12/12 invalid JSON
    # even on the un-quantized original — see scripts/phase5/README.md), so
    # this test can't assert "always produces a good question". What the
    # wrapper actually promises is the contract itself: either a dict with
    # the required keys, or a ValueError — never a malformed silent return.
    generator = QuestionGenerator(model_dir=settings.model2_path)
    generator.load()
    try:
        result = generator.infer("Algebra", difficulty="easy")
    except ValueError:
        return
    assert {"question", "options", "correct_answer"} <= result.keys()
    assert isinstance(result["options"], dict) and result["options"]
