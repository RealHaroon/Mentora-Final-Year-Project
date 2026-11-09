"""
Phase 8 §2.2 — full career flow: register -> CV upload -> rankings ->
roadmap -> start interview -> ask interview.
"""


def _register(client, email):
    resp = client.post("/auth/register", json={
        "first_name": "Test", "last_name": "Career", "email": email,
        "password": "testpass123", "confirm_password": "testpass123",
        "university": "Test University", "exam_goal": "sindh_university",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_career_flow(client):
    headers = _register(client, "career-flow@example.com")

    cv_text = (
        "TECHNICAL SKILLS\nPython, Machine Learning, SQL, TensorFlow\n\n"
        "CERTIFICATIONS\nAWS Certified Cloud Practitioner\n\n"
        "EDUCATION\nBSc Computer Science, GPA 3.6\n"
    )
    files = {"cv_file": ("resume.txt", cv_text.encode(), "text/plain")}
    upload = client.post("/career/cv-upload", headers=headers, files=files)
    assert upload.status_code == 200
    assert len(upload.json()["skills"]) > 0

    rankings = client.get("/career/rankings", headers=headers)
    assert rankings.status_code == 200
    ranking_list = rankings.json()["rankings"]
    assert len(ranking_list) == 5
    scores = [r["match_score"] for r in ranking_list]
    assert scores == sorted(scores, reverse=True), "rankings should be sorted descending by match_score"

    top_career_id = ranking_list[0]["career_id"]
    roadmap = client.get("/career/roadmap", params={"career_id": top_career_id}, headers=headers)
    assert roadmap.status_code == 200
    assert len(roadmap.json()["steps"]) > 0

    start = client.post("/interview/start", params={"career_goal": "data_scientist"}, headers=headers)
    assert start.status_code == 200
    interview_id = start.json()["interview_id"]
    assert start.json()["question"]

    ask = client.post(f"/interview/{interview_id}/ask", headers=headers, json={
        "answer": "I cleaned a messy dataset by imputing missing values with the median and flagging outliers.",
    })
    assert ask.status_code == 200
    assert ask.json()["answer"]


def test_rankings_without_cv_upload_returns_422(client):
    headers = _register(client, "career-flow-no-cv@example.com")
    rankings = client.get("/career/rankings", headers=headers)
    assert rankings.status_code == 422


def test_ask_interview_on_someone_elses_session_is_rejected(client):
    headers_a = _register(client, "career-flow-user-a@example.com")
    headers_b = _register(client, "career-flow-user-b@example.com")

    start = client.post("/interview/start", params={"career_goal": "ml_engineer"}, headers=headers_a)
    interview_id = start.json()["interview_id"]

    ask = client.post(f"/interview/{interview_id}/ask", headers=headers_b, json={"answer": "trying to hijack this session"})
    assert ask.status_code == 404
