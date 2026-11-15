"""
Phase 8 §2.2 — full exam flow, multiple endpoints in sequence, checking the
end state (does the dashboard actually reflect what the exam flow did),
not just one response at a time.
"""


def _register(client, email):
    return client.post("/auth/register", json={
        "first_name": "Test", "last_name": "Student", "email": email,
        "password": "testpass123", "confirm_password": "testpass123",
        "university": "Test University", "exam_goal": "sindh_university",
    })


def test_full_exam_flow(client):
    reg = _register(client, "exam-flow@example.com")
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tt = client.get("/exam/timetable", headers=headers)
    assert tt.status_code == 200
    assert len(tt.json()["rows"]) > 0

    # topic="Algebra" matches the single seeded question for that topic
    # (conftest.py's _seed_minimal_data) — M2 generation almost always fails
    # its own JSON-validity check (documented, see scripts/phase5/README.md),
    # so this deterministically exercises the question-bank fallback path.
    mcq = client.get("/exam/mcq", params={"topic": "Algebra"}, headers=headers)
    assert mcq.status_code == 200
    question = mcq.json()["question"]
    assert len(question["options"]) == 4

    wrong_option = next(o for o in question["options"] if o["value"] != "A")  # seeded correct_answer is "A"
    submit = client.post("/exam/mcq/submit", json={
        "question_id": question["question_id"], "answer": wrong_option["value"],
    }, headers=headers)
    assert submit.status_code == 200
    body = submit.json()
    assert body["correct"] is False
    assert len(body["weak_topics_flagged"]) > 0

    weak = client.get("/dashboard/weak-topics", headers=headers)
    assert weak.status_code == 200
    weak_topics = {t["topic"] for t in weak.json()["topics"]}
    assert set(body["weak_topics_flagged"]) & weak_topics, (
        f"expected an overlap between flagged topics {body['weak_topics_flagged']!r} "
        f"and what /dashboard/weak-topics now reports {weak_topics!r}"
    )


def test_mcq_submit_correct_answer_does_not_flag_anything(client):
    reg = _register(client, "exam-flow-correct@example.com")
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    submit = client.post("/exam/mcq/submit", json={"question_id": "1", "answer": "A"}, headers=headers)
    assert submit.status_code == 200
    body = submit.json()
    assert body["correct"] is True
    assert body["graded_by"] == "dataset"
    assert body["weak_topics_flagged"] == []


def test_mcq_with_no_answer_key_is_graded_by_ai(client, db_session):
    # 2026-11-15 — question_id 3 (conftest.py) has no correct_answer at
    # all, matching the real shape of 1777 of the seeded question bank's
    # 2155 rows. Real Groq call (see test_rag_graceful_degradation.py for
    # the monkeypatched-failure counterpart) — deliberately unambiguous
    # question so this is a reliable assertion, not a flaky one.
    reg = _register(client, "exam-flow-ai-graded@example.com")
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    submit = client.post("/exam/mcq/submit", json={"question_id": "3", "answer": "B"}, headers=headers)
    assert submit.status_code == 200
    body = submit.json()
    assert body["correct"] is True
    assert body["correct_answer"] == "B"
    assert body["graded_by"] == "ai_inferred"

    # Persisted on the shared Question row, not just this response —
    # the next student to get this question should be graded instantly
    # without another Groq call.
    from database.models import Question
    question = db_session.get(Question, 3)
    assert question.correct_answer == "B"
    assert question.correct_answer_source == "ai_inferred"
