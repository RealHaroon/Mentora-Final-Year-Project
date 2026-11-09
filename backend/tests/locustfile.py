"""
Phase 8 §5 — load/concurrency testing against the real running server.

Run: locust -f backend/tests/locustfile.py --host http://localhost:8000
Then open http://localhost:8089 and start with 3-5 simulated users — this
laptop is the target deployment environment, not a server; the question is
"does it hold up for a small in-person demo," not production scale.
"""

import random

from locust import HttpUser, between, task


class Student(HttpUser):
    wait_time = between(2, 5)  # realistic pacing, not a request hammer

    def on_start(self):
        email = f"locust-{random.randint(1, 10**9)}@example.com"
        resp = self.client.post("/auth/register", json={
            "first_name": "Locust", "last_name": "User", "email": email,
            "password": "testpass123", "confirm_password": "testpass123",
            "university": "Load Test U", "exam_goal": "mdcat",
        })
        self.token = resp.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def view_dashboard(self):
        self.client.get("/dashboard/weak-topics", headers=self.headers)

    @task(2)
    def submit_mcq(self):
        self.client.post(
            "/exam/mcq/submit", json={"question_id": "1", "answer": "A"}, headers=self.headers,
        )

    @task(1)
    def generate_question(self):
        # The single heaviest on-demand endpoint — M2 generation (almost
        # always falls through to the question-bank fallback, see
        # scripts/phase5/README.md, but still pays the generation attempt's
        # cost first) serialized against M1 via the shared heavy_lock.
        self.client.get("/exam/mcq", params={"topic": "Algebra"}, headers=self.headers)

    @task(1)
    def topic_explainer(self):
        # Groq-backed, NOT behind heavy_lock (see rag_core/pipeline.py) — a
        # useful contrast against generate_question's queuing behavior.
        self.client.get(
            "/exam/topic-explainer", params={"query": "how do I solve a quadratic equation"}, headers=self.headers,
        )
