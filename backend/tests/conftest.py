"""
Phase 8 §2 — shared fixtures for integration tests.

Deviates from the Phase 8 doc's sketch in two ways, both deliberate:

1. Uses the sync `fastapi.testclient.TestClient`, session-scoped, instead of
   an async `httpx.AsyncClient` + `ASGITransport`. The doc's version never
   triggers FastAPI's lifespan (startup/shutdown) — `ASGITransport` doesn't
   run it unless wrapped with something like `asgi-lifespan`'s
   `LifespanManager`. That matters here specifically because every route
   that touches the Model Manager reads `request.app.state.model_manager`,
   which is only ever set inside `lifespan()`. `TestClient` used as a
   context manager (`with TestClient(app) as client:`) runs the real
   lifespan — the same pattern already verified working end-to-end in
   Phase 6/7's manual e2e scripts.
2. The client fixture is session-scoped (lifespan runs ONCE for the whole
   test run), not function-scoped. `ModelManager` is a singleton — a
   function-scoped client would re-enter `lifespan()` per test, and
   `ModelManager.startup()` isn't idempotent about its background watchdog
   task (it creates a new `asyncio.Task` every call without cancelling the
   previous one), leaking one uncancelled task per test. Running startup
   once avoids that leak and also avoids repeatedly reloading M3/M4's real
   model weights for every single test.

The test DB (function-scoped, fresh per test) is still exactly what the doc
asks for — real production data is never touched by test runs.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, CareerProfile, Question
from database.session import get_db
from services.rate_limit import limiter

TEST_DB_URL = "sqlite:///./test_mentora.db"


@pytest.fixture(scope="session", autouse=True)
def _disable_rate_limiting_by_default():
    # The limiter is a single in-memory counter shared by the whole
    # session-scoped app_client across every test in this run, all from the
    # same fake client IP — real production limits (5-10/minute) get
    # exhausted by cumulative legitimate test traffic within seconds, not by
    # anything resembling abuse. Disabled by default; re-enabled only inside
    # the dedicated test that actually verifies rate limiting works
    # (tests/test_security.py::test_login_rate_limit_eventually_kicks_in).
    limiter.enabled = False
    yield


@pytest.fixture(scope="session")
def app_client():
    import main
    with TestClient(main.app) as client:
        yield client


@pytest.fixture
def db_session():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    _seed_minimal_data(session)

    yield session

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()
    if os.path.exists("./test_mentora.db"):
        os.remove("./test_mentora.db")


def _seed_minimal_data(session):
    # Mirrors backend/scripts/seed_careers.py — the real career_matcher
    # wrapper (always-resident, singleton) is loaded once at app startup
    # against the PRODUCTION database, so its embeddings/catalogue aren't
    # re-built per test; this seed only needs to satisfy routes' own
    # Question/CareerProfile lookups (e.g. /career/rankings' key_skill_gap),
    # which DO go through the per-test overridden session.
    careers = [
        CareerProfile(career_id=1, title="Data Scientist", required_skills=["Python", "Statistics", "Machine Learning"], category="Technology"),
        CareerProfile(career_id=2, title="ML Engineer", required_skills=["Python", "TensorFlow", "MLOps"], category="Technology"),
        CareerProfile(career_id=3, title="Business Analyst", required_skills=["SQL", "Tableau", "Excel"], category="Business"),
        CareerProfile(career_id=4, title="Software Engineer", required_skills=["Python", "System Design", "APIs"], category="Technology"),
        CareerProfile(career_id=5, title="Product Manager", required_skills=["Leadership", "Strategy", "UX"], category="Business"),
    ]
    session.add_all(careers)

    # A handful of real, labeled questions (not the full 2155-row bank) —
    # enough for a deterministic exam-flow test with a known correct answer.
    questions = [
        Question(
            question_id=1, subject="Mathematics", topic="Algebra", subtopic="Quadratic Equations",
            difficulty="medium", question_text="Solve x^2 - 5x + 6 = 0. What are the roots?",
            options={"A": "x = 2, 3", "B": "x = -2, 3", "C": "x = 1, 6", "D": "x = -1, -6"},
            correct_answer="A", source="test fixture",
        ),
        Question(
            question_id=2, subject="Mathematics", topic="Geometry and Trigonometry", subtopic="Triangles",
            difficulty="easy", question_text="A triangle has angles of 50 and 70 degrees. Find the third angle.",
            options={"A": "50", "B": "60", "C": "70", "D": "80"},
            correct_answer="B", source="test fixture",
        ),
    ]
    session.add_all(questions)
    session.commit()


@pytest.fixture
def client(app_client, db_session):
    app_client.app.dependency_overrides[get_db] = lambda: db_session
    yield app_client
    app_client.app.dependency_overrides.pop(get_db, None)
