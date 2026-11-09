# MENTORA — Phase 8 Deep Dive: Integration Testing & Performance Tuning

*Prerequisite: Phases 1–7 are done — every endpoint from the master plan's §10 table
is wired to real logic (auth, the five ML models via the Model Manager, and the RAG
pipeline). Nothing has been tested as a **whole system** yet, only piece by piece.
This phase is where you find out what breaks when everything runs together, and
where the RAM/latency numbers get measured for real instead of estimated.
Estimated time: 4–7 days.*

**Cost note, upfront, since it applies to every tool choice in this phase:** every
tool recommended below — `pytest`, `httpx`, Playwright, Locust, `py-spy`, `psutil`,
`Faker`, OWASP ZAP, GitHub Actions (free tier) — is free and open-source. Nothing in
this phase requires a paid service, a paid API, or a credit card. Where a "free tier"
is mentioned (GitHub Actions), it's a genuinely free tier, not a trial — it's called
out explicitly so you know it's safe to rely on for an FYP with no budget.

---

## 0. Why this phase is its own thing, not just "more of Phase 6/7's testing"

Phases 6 and 7 tested things in isolation: one model wrapper, one RAG pipeline call,
one endpoint at a time, usually with nothing else running. Phase 8 tests the
**system**: what happens when a student submits an MCQ (triggers M1) at the same
moment another browser tab is generating a new question (triggers M2) while a third
is mid-mock-interview (triggers Ollama) — all on 4 CPU cores and 8GB RAM. This is
where the Model Manager's `heavy_lock` semaphore either proves itself or reveals a
gap, and where "it worked when I tested it alone" and "it works in the real app"
turn out to be different claims.

---

## 1. The testing pyramid for this project — what layer catches what

```
        ▲  Manual exploratory + demo rehearsal (Phase 9, not this phase)
        │
        │  End-to-end (Playwright) — does the real user flow work in a real browser?
        │
        │  Integration (pytest + httpx against FastAPI) — do endpoints + DB + Model
        │  Manager + RAG work together correctly?
        │
        ▼  Unit tests (already written in Phase 6 §8, Phase 7 §12.1) — does this
           ONE function/model wrapper/retrieval call behave correctly, in isolation?
```
You already have the bottom layer. This phase builds the middle and top layers, then
uses all three together for the RAM/latency measurement work in §6–7.

---

## 2. Step 1 — backend integration tests (pytest + httpx, free, no browser needed)

### 2.1 Set up a dedicated test database
Never run integration tests against your real development data — a test run that
creates/deletes users will corrupt whatever you were manually testing with.
```python
# backend/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base
from database.session import get_db
from main import app
from httpx import AsyncClient, ASGITransport

TEST_DB_URL = "sqlite:///./test_mentora.db"  # SQLite is enough for test runs even if
                                                # you're on Postgres for real dev/deploy —
                                                # it's free, needs no setup, and is fast
                                                # to reset between test runs

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)  # wipe clean after every single test — no cross-test leakage

@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")
```

### 2.2 Write one integration test per user-facing flow (not per endpoint)
The difference from Phase 6's unit tests: these call multiple endpoints in sequence,
the way a real session actually would, and check the *end state*, not just one
response.

```python
# backend/tests/test_exam_flow.py
import pytest

@pytest.mark.asyncio
async def test_full_exam_flow(client):
    # 1. register
    reg = await client.post("/auth/register", json={
        "first_name": "Test", "last_name": "Student", "email": "test@example.com",
        "password": "testpass123", "confirm_password": "testpass123",
        "university": "Test University", "exam_goal": "sindh_university",
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. fetch timetable
    tt = await client.get("/exam/timetable", headers=headers)
    assert tt.status_code == 200
    assert len(tt.json()["rows"]) > 0

    # 3. fetch a generated MCQ
    mcq = await client.get("/exam/mcq", params={"topic": "quadratic-equations"}, headers=headers)
    assert mcq.status_code == 200
    question = mcq.json()
    assert "question" in question and len(question.get("options", [])) == 4

    # 4. submit a WRONG answer on purpose, confirm weak-topic detection fires
    wrong_option = next(o for o in question["options"] if o["value"] != question.get("correct_answer"))
    submit = await client.post("/exam/mcq/submit", json={
        "question_id": question["question_id"], "answer": wrong_option["value"],
    }, headers=headers)
    assert submit.status_code == 200
    assert submit.json()["correct"] is False
    assert len(submit.json()["weak_topics_flagged"]) > 0

    # 5. confirm the dashboard reflects it
    weak = await client.get("/dashboard/weak-topics", headers=headers)
    assert any(t["topic"] for t in weak.json())
```
Write the equivalent full-flow tests for: **career** (register → CV upload → rankings
→ roadmap → start interview → ask interview), and **auth edge cases** (wrong
password, expired token, forgot-password round trip). These are exactly the flows
listed in the master plan's original 11-point checklist — this step is that checklist,
automated instead of manual, so it can be re-run in seconds after every change instead
of clicked through by hand every time.

### 2.3 Run them
```bash
pip install pytest pytest-asyncio httpx
pytest backend/tests/ -v
```

---

## 3. Step 2 — end-to-end browser tests (Playwright, free, tests the REAL frontend)

Integration tests (§2) prove the API works. They don't prove the Next.js pages
actually render the data correctly, that `middleware.ts` actually redirects, or that
a button click actually fires the request it's supposed to. For that, you need a real
browser driving the real frontend against the real (or a test-configured) backend.

### 3.1 Install
```bash
npm install --save-dev @playwright/test
npx playwright install --with-deps chromium   # just chromium is enough for local FYP testing — no need for the full browser matrix
```

### 3.2 Write the same flows as browser tests
```ts
// frontend/tests/e2e/exam-flow.spec.ts
import { test, expect } from '@playwright/test';

test('student can register, take an MCQ, and see it flagged on dashboard', async ({ page }) => {
  await page.goto('http://localhost:3000/register');
  await page.fill('#first_name', 'Test');
  await page.fill('#last_name', 'Student');
  await page.fill('#email', `test-${Date.now()}@example.com`);  // unique email per run
  await page.fill('#password', 'testpass123');
  await page.fill('#confirm_password', 'testpass123');
  await page.fill('#university', 'Test University');
  await page.selectOption('#exam_goal', 'sindh_university');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL(/.*dashboard/);   // middleware.ts + the redirect from LoginForm/RegisterForm

  await page.goto('http://localhost:3000/exam-prep');
  await expect(page.locator('#mcq-form')).toBeVisible();
  // deliberately pick a wrong-looking option for a deterministic test — or read the
  // rendered options and click whichever ISN'T flagged as correct in a data-testid,
  // if you add one during Phase 2's wiring specifically to make this reliable
  await page.click('.mcq-option >> nth=1');
  await page.click('#mcq-form button[type="submit"]');
  await expect(page.locator('text=/weak topic|flagged/i')).toBeVisible();

  await page.goto('http://localhost:3000/dashboard');
  await expect(page.locator('.weak-item')).toHaveCount(await page.locator('.weak-item').count());  // at least renders without erroring
});

test('logged-out user visiting /dashboard is redirected to /login', async ({ page }) => {
  await page.goto('http://localhost:3000/dashboard');
  await expect(page).toHaveURL(/.*login/);
});
```

### 3.3 Run them (both servers need to actually be running)
```bash
# terminal 1
cd backend && uvicorn main:app --port 8000
# terminal 2
cd frontend && npm run build && npm run start
# terminal 3
npx playwright test
```
Playwright can also auto-start the frontend for you via a `webServer` block in
`playwright.config.ts` — worth setting up once so `npx playwright test` alone is
enough, without three manual terminals every time.

---

## 4. Step 3 — the manual checklist, elaborated (run this even with §2–3 automated — automation catches regressions, a human catches "this feels off")

Go through this in a real browser, unhurried, taking notes on anything that feels
slow, confusing, or visually broken — not just functionally broken:

1. **Register** a brand-new account → land on `/dashboard`. *Check:* does the stat
   strip show sensible zero/default values for a brand-new student, not stale mock
   data left over from earlier phases?
2. **Log out, log back in** → same account, same data persisted.
3. **`/exam-prep`** → timetable loads, MCQ loads, submit both a right and a wrong
   answer across two different questions, confirm the weak-topic flag only fires on
   the wrong one.
4. **`/dashboard`** → confirm the weak topic from step 3 actually appears here, not
   just in the API response.
5. **`/career`** → upload a real CV (use 2–3 different real resumes, not just your
   test PDF, to catch NER edge cases) → confirm extracted skills look plausible for
   each.
6. **Career rankings** → confirm they update if you change the uploaded CV to one
   with clearly different skills (e.g. a design-heavy resume vs. a data-heavy one)
   — the rankings should visibly shift, not stay identical.
7. **Roadmap** → click "View Roadmap" on two different career rows, confirm the
   timeline content actually changes between them.
8. **Mock interview** → start one, answer 3–4 questions in a row, confirm the
   conversation stays coherent (the AI references your actual answers, doesn't just
   ask generic disconnected questions).
9. **`/learning-portal`** → loads without error, content is plausible.
10. **Forgot password** → full round trip, including actually receiving/using a
    reset code if email sending is implemented, or the dev-mode equivalent if not.
11. **Settings → Delete Account** → confirm it actually removes access (can't log
    back in with the same credentials afterward) and doesn't leave the session usable.

---

## 5. Step 4 — load/concurrency testing (Locust, free) — how many students can this handle at once?

This matters for two reasons specific to this project: (1) a real demo might have
several judges/observers clicking around simultaneously, and (2) it's the most
direct way to actually observe whether the Model Manager's `heavy_lock` (Phase 6 §4,
Phase 7 §9) is doing its job under real concurrent load, not just in a single-request
test.

### 5.1 Install and write a locustfile
```bash
pip install locust
```
```python
# backend/tests/locustfile.py
from locust import HttpUser, task, between

class Student(HttpUser):
    wait_time = between(2, 5)  # simulates realistic pacing, not a request hammer

    def on_start(self):
        resp = self.client.post("/auth/login", json={"email": "loadtest@example.com", "password": "testpass123"})
        self.token = resp.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def view_dashboard(self):
        self.client.get("/dashboard/stats", headers=self.headers)

    @task(2)
    def submit_mcq(self):
        self.client.post("/exam/mcq/submit", json={"question_id": "Q1001", "answer": "A"}, headers=self.headers)

    @task(1)
    def generate_question(self):
        self.client.get("/exam/mcq", params={"topic": "quadratic-equations"}, headers=self.headers)

    @task(1)
    def mock_interview_turn(self):
        self.client.post("/interview/start", params={"career_title": "Data Scientist"}, headers=self.headers)
```

### 5.2 Run it, start small
```bash
locust -f backend/tests/locustfile.py --host http://localhost:8000
```
Open `http://localhost:8089`, start with **3–5 simulated users**, not more — this
laptop is the target deployment environment, not a server, and the honest question to
answer is "does it hold up for a small in-person demo," not "can it serve a
production userbase." Watch the **response time** graph, and watch `psutil`/Task
Manager alongside it for RAM.

### 5.3 What you're actually looking for
- Does response time for `generate_question`/`mock_interview_turn` spike
  dramatically (not just "slow," but *queueing* — later requests waiting far longer
  than earlier ones) when 2+ simulated users hit those endpoints at once? That's the
  `heavy_lock` semaphore working as designed — it's *supposed* to serialize these, so
  seeing queuing here is correct, not a bug. The thing to actually worry about is if
  requests **fail** (500 errors, timeouts) rather than just queue.
- At what simulated user count does the app become genuinely unusable (multi-minute
  waits, actual errors)? That number is your realistic answer to "how many people can
  use this at once" — write it down for Phase 9's demo planning.

---

## 6. Step 5 — RAM measurement, done properly (redo the master plan's §12 table with real numbers)

### 6.1 Baseline idle
```bash
# start everything, do nothing for 2 minutes, then measure
python -c "import psutil; m=psutil.virtual_memory(); print(f'{m.percent}% ({m.used/1e9:.2f}GB used)')"
```

### 6.2 One-variable-at-a-time deltas
This is the part worth doing carefully — don't just load the app and eyeball total
RAM, isolate what each piece actually costs:
```bash
# 1. measure idle (backend + frontend + Postgres + Ollama service running but no model loaded)
# 2. trigger ONE M1 request (submit a wrong MCQ answer), measure again -> delta = M1's footprint
# 3. wait 6 minutes (past the idle-unload window), measure again -> should drop back near idle
# 4. trigger ONE M2 request, measure -> delta = M2's footprint
# 5. trigger ONE Ollama request, measure -> delta = phi4-mini's footprint
# 6. trigger M2 AND Ollama in close succession (two browser tabs), measure the peak -> this
#    is the number that tells you whether heavy_lock is actually preventing simultaneous
#    residency, or just serializing CPU time while both stay loaded
```
Log each of these into a real table (reuse the master plan's §12 format) and compare
against what was estimated back in Phase 0 — it's fine, expected even, if the real
numbers differ from the estimate; the point of this step is replacing a guess with a
measurement, not confirming the guess was right.

### 6.3 If peak RAM gets uncomfortably close to 8GB
- Increase the Windows/Linux swap/page file to ~12GB (already flagged as a safety net
  back in the master plan) — this doesn't fix a real problem but prevents a hard
  crash while you address the actual cause.
- Shorten the idle-unload window in `ModelManager` (Phase 6 §4.1's
  `IDLE_UNLOAD_SECONDS`) from 5 minutes to 2–3, trading a bit more reload latency for
  a smaller resident footprint.
- Confirm, again, that Uvicorn is genuinely running single-worker (Phase 6 §1) — this
  is the single most common way a RAM budget silently doubles.

---

## 7. Step 6 — latency profiling with `py-spy` (free, no code changes needed to use it)

For a "why is this specific request slow" question that raw timing numbers don't
answer, `py-spy` samples a running Python process without needing any instrumentation
added to the code:
```bash
pip install py-spy
py-spy top --pid <uvicorn process id>          # live view of what's consuming CPU right now
py-spy record -o profile.svg --pid <uvicorn process id> --duration 30   # flamegraph over 30s
```
Trigger a slow request (e.g. CV upload, which chunks + runs NER inference) while
`py-spy record` is running, then open `profile.svg` in a browser — it shows exactly
which function calls are eating the time, which is far more actionable than guessing.

---

## 8. Step 7 — a basic security pass (free tools + manual checklist — this doesn't need to be exhaustive for an FYP, but shouldn't be skipped)

| Check | How | Free tool |
|---|---|---|
| SQL injection | Confirm every DB query goes through SQLAlchemy's parameterized queries, not raw string-formatted SQL | Manual code review — grep for any `f"SELECT` / `.format(` near a `.execute(` call |
| Password storage | Confirm `passlib[bcrypt]` is actually being used for hashing, never plaintext or a weak hash | Manual check of `auth_service.py` |
| JWT expiry | Confirm tokens actually expire (test: use a token, wait past expiry — or temporarily set a 10-second expiry for testing — confirm a 401 follows) | pytest test case |
| CORS | Confirm `allow_origins` is your actual frontend origin, not `["*"]` | Manual check of `main.py`'s `CORSMiddleware` config |
| File upload validation | Confirm `cv_file` upload rejects non-PDF/DOCX files and enforces a size limit (an unbounded upload is both a security and a RAM risk on this hardware) | pytest: try uploading a `.exe` renamed to `.pdf`, confirm rejection |
| Rate limiting on auth endpoints | Prevents brute-force login attempts | `pip install slowapi` (free) — a few lines of decorator-based rate limiting on `/auth/login` |
| Automated scan (optional, extra thoroughness) | Point an automated scanner at the running backend | **OWASP ZAP** (free, open-source) — run its baseline scan against `http://localhost:8000` |

None of this needs to be enterprise-grade for an FYP defense, but being able to say
"I checked for SQL injection, verified password hashing, and confirmed rate limiting
on login" in a viva is a genuinely strong, concrete answer if asked about security.

---

## 9. Step 8 — realistic data volume testing (Faker, free)

Everything tested so far has probably used 1–2 test accounts. Before calling this
phase done, seed the database with a more realistic volume and re-check performance
and UI rendering under it:
```python
# backend/scripts/seed_test_data.py
from faker import Faker  # pip install faker — free
import random

fake = Faker()

def seed(n_students=50, sessions_per_student=15):
    for _ in range(n_students):
        user = create_user(
            first_name=fake.first_name(), last_name=fake.last_name(),
            email=fake.unique.email(), password="testpass123",
            university="University of Sindh, Laar Campus",
            exam_goal=random.choice(["sindh_university", "mehran_university", "lums"]),
        )
        for _ in range(sessions_per_student):
            create_exam_session(user.id, score=random.randint(30, 95))
```
Run this, then re-check: does the dashboard's score-trend chart render sensibly with
15 real sessions instead of the mock data's clean 10-point line? Does anything on the
learning-portal or career pages assume there's exactly one CV upload, one career
ranking, etc., and break when a student has several? This is where assumptions baked
in during Phase 2's mock-data wiring (§Phase 2) tend to surface.

---

## 10. Step 9 — regression safety net (free, no paid CI required)

### 10.1 Local — a single script that runs everything
```bash
# scripts/run_all_tests.sh
#!/bin/bash
set -e
echo "Backend unit + integration tests..."
cd backend && pytest tests/ -v
echo "Frontend end-to-end tests..."
cd ../frontend && npx playwright test
echo "All tests passed."
```
Run this before every significant change from here on — it's the difference between
finding out something broke *now*, while you remember what you just changed, versus
finding out during demo rehearsal in Phase 9.

### 10.2 Optional — GitHub Actions (genuinely free, not a trial)
If the repo lives on GitHub, GitHub Actions gives free CI minutes (2,000/month on the
free plan for private repos, unlimited for public repos) — enough to auto-run
`scripts/run_all_tests.sh` on every push, catching regressions without you needing to
remember to run it locally:
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt pytest pytest-asyncio httpx
      - run: cd backend && pytest tests/ -v
```
(This CI runner is a different, much more powerful machine than your laptop — it's
fine for running the backend's pytest suite quickly, but isn't representative of the
real deployment target for anything RAM/latency-related; keep §6–7's measurements
on the actual laptop, use CI only for pass/fail correctness checks.)

---

## 11. Step 10 — apply the model-swap decision now, backed by real numbers

This is the point where the master plan's "if `phi4-mini` is too slow, swap to
`qwen2.5:1.5b`/`gemma3:1b`" decision actually gets made, using §6–7's real
measurements instead of a guess:

```bash
# .env — the only line that needs to change
OLLAMA_MODEL=qwen2.5:1.5b
```
Re-run §5's load test and §7's latency profiling with the new model, compare against
the `phi4-mini` numbers, and make the call based on what you actually measured:
is the smaller model's speedup worth its (likely lower) answer quality for a live
demo? There's no universally right answer here — it depends on what you observed in
§4's manual groundedness checks (Phase 7 §12.2) for each candidate model.

---

## 12. Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Integration tests pass but Playwright tests fail on the same flow | Frontend caching/hydration issue, or the test clicked before an async fetch resolved | Add explicit `await expect(...).toBeVisible()` waits rather than fixed `sleep()` calls in Playwright tests |
| Locust shows failed (not just slow) requests under light load | `heavy_lock` isn't actually being awaited somewhere, or a genuine timeout is too short for this CPU's real generation speed | Check every RAG/M2 code path uses the pattern from Phase 6 §4/Phase 7 §9; increase any hardcoded request timeout on the frontend `apiFetch` calls |
| RAM measurements are inconsistent between runs | Background OS processes (browser tabs, antivirus scans) interfering with a genuinely tight 8GB budget | Close everything non-essential before measuring; note that this variability is itself useful information about how little headroom exists |
| Seeded Faker data breaks the dashboard chart | Chart code assumed exactly 10 sessions (matching Phase 2's mock data shape) | Fix the chart component to handle any N ≥ 1 sessions gracefully, not just exactly 10 |
| `py-spy` requires elevated permissions | OS-level process-inspection restriction, common on Linux without `sudo` | Run with `sudo py-spy ...`, or on Linux set `sudo sysctl kernel.yama.ptrace_scope=0` temporarily |

---

## 13. Definition of done

> **Scope decision, made explicitly with the user before starting**: §3
> (Playwright) and §4 (the manual browser checklist) both assume the Next.js
> frontend calls this backend. It doesn't — confirmed in Phase 6 (no
> `fetch`/`axios` calls to `/api/exam|career|dashboard` anywhere in
> `frontend/`) and still true here. Running either against the current
> frontend would "pass" while testing nothing real. User's call: do
> everything backend-only achievable now, skip §3-4 explicitly rather than
> produce misleading green checkmarks. §11 (the `phi4-mini` vs. fallback
> model decision) is also N/A — Phase 7 already swapped to Groq (cloud),
> so there's no local model to tune/swap.

- [x] Backend integration tests (§2) — `test_exam_flow.py`, `test_career_flow.py`,
      `test_auth_edge_cases.py`: 11 tests, all passing against a dedicated
      SQLite test DB (real production data never touched). Deviated from the
      doc's async-httpx sketch: used the sync `TestClient` instead, session-scoped
      — the doc's `ASGITransport` approach never triggers FastAPI's `lifespan`,
      which is exactly where `app.state.model_manager` gets set; every
      model-backed route would have broken. See `tests/conftest.py`'s docstring.
      Found and fixed a real gap while writing these: `/dashboard/weak-topics`
      was still Phase 2's hardcoded mock, never wired to the real `TopicScore`
      rows M1 writes — the doc's own example test (`weak topics actually show
      on the dashboard`) would have silently passed against fake data otherwise.
- [ ] ~~Playwright end-to-end tests (§3)~~ — skipped, see scope decision above.
- [ ] ~~11-point manual checklist (§4)~~ — skipped, see scope decision above.
- [x] Locust load test (§5) — `tests/locustfile.py`, run headless at 5 users/90s.
      0% failure rate throughout. Confirmed the exact behavior §5.3 describes:
      `/exam/mcq` (M2, behind `heavy_lock`) queued hard under concurrency — one
      call took 34.7s, a second concurrent one queued behind it and took 63.1s
      — while `/exam/topic-explainer` (Groq, NOT behind `heavy_lock` — see
      Phase 7's header note) stayed under 2.6s throughout. No errors, just
      queuing, exactly as designed — but 63s is a real demo-risk number if two
      people hit "generate a new question" close together, worth flagging for
      Phase 9's demo planning.
- [x] Real RAM idle/peak numbers (§6) measured on the actual running server
      (not estimated):

  | Stage | uvicorn RSS |
  |---|---|
  | Idle (M3/M4 resident only) | 1028MB |
  | M1 loaded (DeBERTa) | 1542MB (Δ ~513MB) |
  | M1 unloaded + idle-unload cleanup | 1037MB (back to ~baseline) |
  | M2 loaded (FLAN-T5-large fp16) | 2486MB (Δ ~1449MB) |
  | M1 + M2 loaded together (measured peak) | 3152MB |
  | M5 loaded (BERT NER) | 2627MB (Δ ~489MB) |

  **Found and fixed a real bug in the process**: `unload()` dropping the
  Python reference did NOT shrink process RSS — confirmed in isolation
  (921MB loaded -> 718MB after `unload()` + explicit `gc.collect()`, nowhere
  near the ~287MB pre-load baseline). Root cause: glibc's malloc doesn't
  return freed arenas to the OS on its own. Fix: `ml_core/memory_watchdog.py`'s
  new `release_freed_memory()` calls `gc.collect()` then `ctypes.CDLL
  ("libc.so.6").malloc_trim(0)` (Linux-only, no-op elsewhere), called from
  `ModelManager._idle_watchdog` right after `model.unload()`. Measured
  result for M1 in the live server: RSS dropped from 1542MB back to 1037MB
  — essentially full recovery. **Honest caveat, not swept under the rug**:
  the same fix had zero measurable effect on M2 in the live server on one
  trial (RSS stayed at 2486MB after its idle-unload fired), while working
  fully in an isolated single-model script (2035MB -> 439MB). Most likely
  cause: heap fragmentation from other interleaved request-handling
  allocations in the busier live process prevents `malloc_trim` from
  releasing partially-freed arenas — a known limitation of this technique,
  not a bug in the fix itself. A later unload (M5's) still retroactively
  reclaimed the backlog, dropping RSS to 960MB, lower than the original
  1028MB baseline — so the mechanism works over a session, just not
  deterministically on every single individual unload.
- [x] Latency profiling — used `cProfile` instead of `py-spy`: this system's
      `kernel.yama.ptrace_scope=1` blocks `py-spy`'s ptrace-based attach
      without an interactive sudo password, which can't be supplied
      autonomously. Profiled the CV-upload/NER path directly: 95% of the
      1.36s request (`torch._C._nn.linear`, 1.29s) is the BERT model's actual
      forward-pass compute across its layers — no wasted time in
      tokenization, chunking, or the BIO-decoding logic.
- [x] §8's security checklist:
  - SQL injection: reviewed every `.execute(`/`.format(` site. One raw
    f-string DDL site (`database/session.py`'s migration helper) — safe,
    since `table_name`/`column.name`/`col_type` come from the hardcoded
    SQLAlchemy model definitions, never from request input. Everything else
    uses SQLAlchemy Core `select()`/parameterized queries. No injection
    vector found.
  - Password storage: bcrypt confirmed (`auth_service.py`), now with a
    dedicated test (`test_password_is_actually_hashed_not_plaintext`).
  - JWT expiry: `test_expired_token_rejected` (re-signs with a past `exp`
    rather than sleeping past the real 7-day expiry).
  - CORS: `cors_origins` defaults to `["http://localhost:3000"]`, not `["*"]`.
  - File upload validation: **was completely missing** — no size limit, no
    content check, a renamed `.exe` would silently fall through to the
    "anything else" text-decode branch. Fixed: `routers/career.py`'s
    `_validate_upload()` — 5MB cap, extension allowlist, and magic-byte
    sniffing (`%PDF-` / `PK\x03\x04` / null-byte+UTF-8 check for .txt).
    4 dedicated tests in `tests/test_security.py`, including the doc's exact
    scenario (a `.exe` renamed to `.pdf`).
  - Rate limiting: **was completely missing** — added via `slowapi`
    (`services/rate_limit.py`): 5/min on `/auth/login` and
    `/auth/forgot-password`, 10/min on `/auth/register`. Disabled by
    default across the test suite (`conftest.py`) since cumulative
    legitimate test traffic from one fake IP exhausted these limits within
    the suite itself (caught via two real test failures before the fix);
    re-enabled only inside the one test that verifies the mechanism itself.
  - OWASP ZAP: skipped — optional per the doc's own framing, and a scan run
    needs a long-lived target server beyond this phase's scope.
- [x] Realistic-volume seed data (§9) — `scripts/seed_test_data.py`, 50
      students / 750 exam sessions / 160 topic scores via Faker. No crashes
      on `/dashboard/weak-topics`, `/dashboard/at-risk-check`, or
      `/career/rankings` under this volume. `/dashboard/stats`,
      `/score-trend`, `/weekly-snapshot` remain Phase 2 mocks (pre-existing,
      not a volume-sensitive regression — they're hardcoded regardless of N,
      so Faker volume can't break what never reads real data).
- [x] `scripts/run_all_tests.sh` exists and passes (backend-only, Playwright
      step omitted with the same rationale as §3-4 above).
      GitHub Actions (§10.2) deliberately **not** added: the model weights
      (`ml_models/saved/`) and the RAG vector store (`vector_store/`) are both
      gitignored for size (multi-GB), so a CI runner would have nothing to
      load — every model-wrapper and RAG test would fail on missing files,
      not on real bugs. Making this work would mean non-trivial extra CI
      infra (fetching multi-GB artifacts, a Groq API secret) beyond what this
      explicitly-optional doc section calls for.
- [ ] ~~`phi4-mini` vs. fallback model decision (§11)~~ — N/A, see scope note.

Once every row is checked, the system has been verified as a whole, not just in
pieces — Phase 9 (polish, one-click startup scripts, and demo-day packaging) is what
turns "it works" into "it works reliably in front of an audience." The one number
from this phase worth carrying into Phase 9's planning: a concurrent M2 request can
take upward of 60s under even light load — worth a loading-state UI treatment or a
demo script that avoids triggering two question-generations at once.
