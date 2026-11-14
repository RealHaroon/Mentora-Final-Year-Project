# Mentora — Project Workflow Overview

Written 2026-11-14 as a plain-language orientation to the project for
whoever is picking this up without having written the original phase docs
themselves. It covers two different things on purpose: how the project was
**built** (the phase sequence in `docs/phases/`) and how it actually
**runs** (the live architecture) — those are not the same story, and
conflating them is the easiest way to get lost in this repo.

For "how do I get it running on my machine," see the root `README.md`
instead — this doc is about understanding the system, not operating it.

---

## 1. The big idea

Mentora is three student-facing journeys sharing one brain:

1. **Exam Prep** — AI-generated study timetable, adaptive MCQ practice,
   automatically detected weak topics (from wrong answers, not
   self-reporting).
2. **Career Counseling** — upload a CV → get ranked against career
   profiles by skill similarity → get a concrete 6-month roadmap closing
   the gap to a chosen career.
3. **Learning Portal** — a personal library (video playlist, MCQ
   assignments, course materials) that the other two journeys feed into,
   not a separate standalone feature.

The thing conceptually tying all three together is the **Student
Intelligence Profile (SIP)** — one record per student holding their skill
vector, topic scores, career rankings, and roadmap. Most features read
from or write to data that traces back to this, even where the actual
DB table is more specific (e.g. `TopicScore`, `CareerRanking`, `Roadmap`)
than one single SIP table.

---

## 2. How it was built — the 10 phases (`docs/phases/`)

| Phase | What it did |
|---|---|
| 1 | Built the Next.js frontend — 8 pages, no backend yet. |
| 2 | Wired every button/form in that frontend to a real FastAPI backend — but every endpoint returned **hardcoded fake JSON**. The point of this phase was proving the plumbing worked, before any model existed. |
| 3 | Built the 5 training datasets. |
| 4 | Trained the 5 ML models on Google Colab's free GPU. |
| 5 | Shrank the trained models (quantization/export) so they'd actually fit and run on this project's 8GB-RAM, no-GPU laptop. |
| 6 | Built the **Model Manager** and swapped Phase 2's fake JSON for real model output, one endpoint at a time. |
| 7 | Built the RAG chatbot behind topic explanations and mock interviews. Originally planned as local Ollama; switched to **Groq** (a free cloud LLM API) because local generation was too slow on this hardware — a disclosed, deliberate trade-off, not a shortcut taken quietly. |
| 8 | Integration-tested the whole system together as one piece (not feature-by-feature), and measured real RAM/latency numbers instead of estimating them. |
| 9 | Demo-day polish — pre-caching known-good interactions, rehearsal practices, what's safe to disclose openly to a supervisor vs. what needs fixing. |
| 10 | Final documentation + the material the thesis itself draws from (model evaluation metrics, viva prep). |

**Everything done in sessions after Phase 10** (roadmap persistence, real
notifications, the extra careers, the M2 retry fix, etc.) is
**post-completion maintenance** on top of an already-"finished" system —
mostly closing gaps the original phases left behind (Phase 2's fake JSON
that never actually got replaced in a few places, like the Learning
Portal and Notifications originally were) or features added on direct
request. It is not part of the original 10-phase plan, and isn't
documented under `docs/phases/` for that reason — this file, and ongoing
git commit messages, are where that later work is actually documented.

---

## 3. How it actually runs — the live architecture

**Frontend** (`frontend/`): Next.js (App Router, TypeScript). Calls the
backend over HTTP. As of the 2026-11-10 drift-check audit (see
`docs/phase10/drift_check.md`), nothing in it is hardcoded/fake anymore.

**Backend** (`backend/`): FastAPI. Organized as:

- `routers/` — one file per feature area (`exam.py`, `career.py`,
  `learning.py`, `dashboard.py`, `notifications.py`, `interview.py`,
  `auth.py`, ...). This is where an incoming request lands first.
- `database/models.py` — the real DB tables (SQLite in dev, Postgres-ready).
- `ml_core/` — the 5 trained model wrappers, plus the **Model Manager**
  (`ml_core/model_manager.py`) that decides when each one loads/unloads.
- `rag_core/` — the 3 RAG pipelines (exam / career / interview), each
  backed by its own ChromaDB collection and Groq for generation.
- `services/` — small shared pieces used across routers (e.g.
  `notification_service.py`'s `notify_once`, `auth_service.py`).
- `scripts/` — one-time/operational scripts: seeding data, starting
  servers, pre-warming models.

**The 5 trained models** — only 2 stay loaded in RAM at all times; the
other 3 load on demand and idle-unload after 5 minutes
(`ml_core/model_manager.py`'s `IDLE_UNLOAD_SECONDS`):

| | Model | Always resident? | Does what |
|---|---|---|---|
| M1 | Gap Classifier (DeBERTa) | No (lazy) | Flags weak topics from a wrong MCQ answer. |
| M2 | Question Generator (FLAN-T5-Large + LoRA) | No (lazy) | Tries to generate a fresh MCQ. Known weak since Phase 5's own parity check (12/12 invalid JSON); near-certainly falls back to the real question bank every time — confirmed 2026-11-13 across all 20 real topics. Its retry-on-failure loop was removed the same day since retries never once succeeded. |
| M3 | Trajectory Predictor (LSTM) | **Yes** | Predicts whether a student's score trend is declining, from their last 5 scored exam sessions. |
| M4 | Career Matcher (Sentence-Transformers, all-mpnet-base-v2) | **Yes** | Ranks a student's extracted skills against every seeded career profile by semantic similarity. |
| M5 | CV NER Extractor (BERT) | No (lazy) | Pulls skills/GPA/certifications/degrees out of an uploaded CV. |

The lazy models (M1/M2/M5) share one semaphore — only one of them loads
or runs inference at a time, since this machine can't afford two heavy
models in RAM simultaneously.

**The 3 RAG pipelines** (`rag_pipelines/*/content/`, ingested into
ChromaDB via each pipeline's `ingest.py`):

- **Exam RAG** — grounds topic explanations.
- **Career RAG** — grounds career-profile Q&A and roadmap milestone
  explanations.
- **Interview RAG** — grounds mock-interview questions/feedback.

All three retrieve from their own ChromaDB collection, then call Groq to
generate the actual answer from that retrieved context — "retrieval
augmented," not open-ended generation.

---

## 4. A concrete request-to-response example

Walking the Exam Prep → Career Counseling → Learning Portal chain, since
it touches most of the pieces above:

1. A student answers an MCQ wrong on `/exam-prep`. `routers/exam.py`
   calls M1 (gap classifier) → a `TopicScore` row gets updated → a real
   notification fires via `services/notification_service.py`.
2. The student uploads a CV on `/career`. `routers/career.py` calls M5 to
   extract skills, then M4 to rank them against all 10 seeded career
   profiles. Viewing a roadmap for a chosen career **generates it on
   first view** from that career's `required_skills` plus a
   RAG-grounded (Career RAG) explanation per skill — roadmaps are not
   hand-written content sitting in a table anywhere.
3. The student adds a roadmap-suggested video to their playlist. That
   goes through the exact same `/learning/playlist` endpoint Exam Prep's
   own "add to playlist" button already used — another real
   notification fires from the same shared service.

Nothing in that chain is separate systems bolted together after the
fact — it's one database, one set of models, one notification service,
reused across all three journeys, which is what "one shared brain" in
§1 actually means in code.

---

## 5. Where to go deeper

- Root `README.md` — how to actually run the project (setup, seeding,
  starting servers, running tests).
- `docs/phase10/model_results_table.md` — the real evaluation metrics for
  the 5 trained models; this is the academic core of the thesis.
- `docs/phase10/viva_question_bank.md` — written specifically to prepare
  for defense/viva questions, including ones about known model weaknesses.
- `docs/phase10/drift_check.md` — the 2026-11-10 audit that found and
  fixed frontend/backend drift Phases 8-9 had mistakenly assumed didn't
  exist.
- `docs/phases/MENTORA_Phase9_Polish_Demo_Packaging.md` — demo-day
  practices: what's safe to pre-cache, and what to disclose openly to a
  supervisor rather than try to hide.
- Git commit history (`git log`) — the actual, up-to-date record of every
  post-Phase-10 change, each with a "why," since this file is a snapshot
  and the commits are the living history.
