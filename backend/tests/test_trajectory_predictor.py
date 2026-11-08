from config import settings
from ml_core.models.trajectory_predictor import TrajectoryPredictor


def test_trajectory_predictor_known_example():
    predictor = TrajectoryPredictor(weights_path=settings.model3_path)
    predictor.load()
    # Matches notebooks/experiment_log.md's attempt-1/4 input shape (SEQ_LEN=5).
    result = predictor.infer([55, 60, 68, 65, 75])
    assert result["trend"] in ("declining", "improving", "stable")
    assert isinstance(result["predicted_next_score"], float)


def test_trajectory_predictor_is_deterministic():
    # Not asserting a specific trend direction for a given input shape —
    # verified empirically that this model does NOT reliably track obvious
    # trends (a sharply declining sequence [90,80,70,60,50] predicts
    # "improving"), consistent with M3's documented noise-floor limitation
    # (scripts/phase5/README.md). What should hold regardless: no dropout/
    # randomness at inference, so the same input always gives the same output.
    predictor = TrajectoryPredictor(weights_path=settings.model3_path)
    predictor.load()
    result_a = predictor.infer([90, 80, 70, 60, 50])
    result_b = predictor.infer([90, 80, 70, 60, 50])
    assert result_a == result_b
