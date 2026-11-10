"""
Phase 9 §5 — RAG features must degrade gracefully (503 + a clear message)
when Groq fails, not take down the whole app with a raw 500. This is a
real demo-day risk the Phase 7/8 work didn't originally cover: generation
now depends on Groq (cloud), not local Ollama, so a Groq outage/rate-limit/
timeout is a failure mode this app can actually hit that the original
"everything runs local" plan never anticipated.
"""

from langchain_groq import ChatGroq

from database.models import InterviewQa, InterviewSession
from routers import career, exam, interview

BAD_LLM_KWARGS = {"model": "openai/gpt-oss-120b", "api_key": "gsk_totally_invalid_000000000000000000000", "max_tokens": 50}


def _register(client, email):
    resp = client.post("/auth/register", json={
        "first_name": "Degrade", "last_name": "Test", "email": email,
        "password": "testpass123", "confirm_password": "testpass123",
        "university": "Test University", "exam_goal": "sindh_university",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_topic_explainer_returns_503_not_500_on_groq_failure(client, monkeypatch):
    headers = _register(client, "degrade-exam@example.com")
    monkeypatch.setattr(exam._exam_rag, "llm", ChatGroq(**BAD_LLM_KWARGS))

    r = client.get("/exam/topic-explainer", headers=headers, params={"query": "how do I solve a quadratic equation"})
    assert r.status_code == 503
    assert "temporarily unavailable" in r.json()["detail"].lower()


def test_career_ask_returns_503_not_500_on_groq_failure(client, monkeypatch):
    headers = _register(client, "degrade-career@example.com")
    monkeypatch.setattr(career._career_rag, "llm", ChatGroq(**BAD_LLM_KWARGS))

    r = client.get("/career/ask", headers=headers, params={"query": "what skills do I need to become a data scientist"})
    assert r.status_code == 503
    assert "temporarily unavailable" in r.json()["detail"].lower()


def test_interview_start_returns_503_and_creates_no_partial_session(client, db_session, monkeypatch):
    headers = _register(client, "degrade-interview@example.com")
    monkeypatch.setattr(interview._interview_rag, "llm", ChatGroq(**BAD_LLM_KWARGS))

    before = db_session.query(InterviewSession).count()
    r = client.post("/interview/start", headers=headers, params={"career_goal": "data_scientist"})
    assert r.status_code == 503
    assert "temporarily unavailable" in r.json()["detail"].lower()
    # The RAG call fails before any DB write — confirms no orphaned session
    # row gets created that the student could never actually use.
    assert db_session.query(InterviewSession).count() == before


def test_interview_ask_returns_503_and_does_not_lose_the_students_answer(client, db_session, monkeypatch):
    headers = _register(client, "degrade-interview-ask@example.com")
    start = client.post("/interview/start", headers=headers, params={"career_goal": "ml_engineer"})
    interview_id = start.json()["interview_id"]

    monkeypatch.setattr(interview._interview_rag, "llm", ChatGroq(**BAD_LLM_KWARGS))
    r = client.post(f"/interview/{interview_id}/ask", headers=headers, json={"answer": "my real answer"})
    assert r.status_code == 503

    # The turn must still show as unanswered (not silently marked answered
    # with no feedback) so the student can retry the same /ask call.
    row = db_session.query(InterviewQa).filter(InterviewQa.interview_id == interview_id).one()
    assert row.student_answer is None
