"""
Pre-warms the 3 lazy-loaded models (M1 gap_classifier, M2 question_generator,
M5 cv_ner) before a demo, so ModelManager's 5-minute idle-unload + this
machine's RAM-constrained cold-load doesn't show up as "slow" live in front
of someone. M3/M4 are already always-resident — nothing to do for those.

Does this the same way a real user would: logs in and calls the real
/exam/mcq, /exam/mcq/submit, and /career/cv-upload endpoints against an
ALREADY-RUNNING backend — no shortcut code path, no new dependency, no
sudo, nothing outside this app's own localhost API. The only side effects
are the same ones those real actions always have: one deliberately-wrong
MCQ submission (reinforces the demo account's existing "Algebra is weak"
story — see seed_demo_account.py) and one CV re-upload (adds a CvUpload
row; career rankings/roadmap already key off the latest one).

Run with the backend already started, as whichever account you'll actually
demo with:
  cd backend && ~/.venvs/mentora-backend/bin/python scripts/warm_models.py [email] [password]
"""

import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.models import Question  # noqa: E402
from database.session import SessionLocal  # noqa: E402

BASE_URL = "http://localhost:8000"
DEFAULT_EMAIL = "demo@mentora.pk"
DEFAULT_PASSWORD = "MentoraDemo2026!"
CV_FILE = Path(__file__).resolve().parents[1] / "uploads" / "cv" / "54_cv_test.txt"


def _login(email: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def _pick_gradable_question() -> tuple[str, str]:
    # A real question-bank row with a labeled correct_answer — only a wrong
    # answer to one of these actually runs M1 (see routers/exam.py's
    # submit_mcq: "generated" and unlabeled questions are never graded).
    # Picked directly from the DB rather than depending on M2's own
    # generation happening to fail its validity check in get_mcq.
    db = SessionLocal()
    try:
        q = (
            db.query(Question)
            .filter(Question.correct_answer.is_not(None), Question.correct_answer != "")
            .first()
        )
        if q is None:
            raise RuntimeError("No gradable question in the question bank")
        wrong = next(k for k in (q.options or {}) if k != q.correct_answer)
        return str(q.question_id), wrong
    finally:
        db.close()


def _warm(name: str, fn) -> None:
    start = time.time()
    try:
        fn()
        print(f"  {name}: warmed in {time.time() - start:.1f}s")
    except Exception as e:
        print(f"  {name}: FAILED — {e}")


def main():
    email = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMAIL
    password = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PASSWORD
    print(f"Warming models against {BASE_URL} as {email} ...")

    try:
        token = _login(email, password)
    except requests.RequestException as e:
        print(f"Login failed — is the backend running on {BASE_URL}? ({e})")
        sys.exit(1)
    headers = {"Authorization": f"Bearer {token}"}

    def warm_m2():
        r = requests.get(f"{BASE_URL}/exam/mcq", params={"topic": "Algebra"}, headers=headers, timeout=60)
        r.raise_for_status()

    def warm_m1():
        question_id, wrong_answer = _pick_gradable_question()
        r = requests.post(
            f"{BASE_URL}/exam/mcq/submit",
            json={"question_id": question_id, "answer": wrong_answer},
            headers=headers,
            timeout=60,
        )
        r.raise_for_status()

    def warm_m5():
        with open(CV_FILE, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/career/cv-upload",
                files={"cv_file": (CV_FILE.name, f, "text/plain")},
                headers=headers,
                timeout=60,
            )
        r.raise_for_status()

    _warm("M2 question_generator", warm_m2)
    _warm("M1 gap_classifier", warm_m1)
    _warm("M5 cv_ner", warm_m5)
    print("Done. M3/M4 are always resident; M1/M2/M5 are now loaded into RAM.")
    print("Re-run this if more than 5 idle minutes pass before you actually demo.")


if __name__ == "__main__":
    main()
