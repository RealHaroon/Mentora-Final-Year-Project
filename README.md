# Mentora — Final Year Project

An AI-assisted exam-prep and career-guidance platform: a trained-model backend
(gap classifier, question generator, trajectory predictor, career matcher, CV
parser) plus a RAG-based chatbot (Groq + ChromaDB) for topic explanations and
mock interviews. Full phase-by-phase technical history lives in
`docs/phases/` — this file is just "how do I get it running," consolidated
from each phase's own setup notes per
`docs/phases/MENTORA_Phase9_Polish_Demo_Packaging.md` §8.

## Current state

- **Backend**: fully real — database-backed auth, all 5 trained models wired
  through a Model Manager (Phase 6), RAG chatbot wired (Phase 7), integration-
  tested (Phase 8).
- **Frontend**: wired to the real backend (Phase 2) and calling real
  endpoints throughout. **Correction**: Phases 8 and 9's docs state the
  frontend "isn't wired" and scope backend-only work on that basis — that
  was wrong; Phase 2 wired it before either phase started, just against
  response shapes that Phases 6-7 later changed without the frontend being
  revisited. A 2026-11-10 audit found and fixed the resulting drift. See
  `frontend/README.md` and `docs/phase10/drift_check.md`.

## 1. Get the trained models and vector store (not in git — too large)

```
mentora_models/   ~3.6GB  — Phase 4 raw training outputs
ml_models/        ~2.5GB  — Phase 5's packaged/quantized form the backend actually loads
vector_store/      small  — ChromaDB's on-disk index (rebuildable, see below)
```

`ml_models/` and `mentora_models/` are gitignored. Either:
- Download them from the project's Google Drive (ask whoever has `mentora_models/`
  access — see `docs/phases/MENTORA_Phase5_Export_Optimize_UPDATED.md` for the
  exact folder layout), or
- Regenerate `ml_models/saved/` from scratch by running Phase 4's Colab
  notebooks (`notebooks/`) then Phase 5's quantization scripts
  (`scripts/phase5/`).

`vector_store/` is also gitignored but cheap to rebuild locally once the repo
is cloned — see step 4 below.

## 2. Backend setup

This repo lives on a path containing a colon (`Local Disk (D:)`), and
Python's `venv` refuses to create a virtualenv inside any path containing
`:` — so the venv lives outside the repo, in the home directory:

```bash
python3 -m venv ~/.venvs/mentora-backend
~/.venvs/mentora-backend/bin/pip install -r backend/requirements.txt
```

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` and set `GROQ_API_KEY` (free key at
[console.groq.com/keys](https://console.groq.com/keys) — use one dedicated to
this project, not shared with another). SQLite works out of the box for
everything else, no further setup needed.

## 3. Seed the database

```bash
cd backend
~/.venvs/mentora-backend/bin/python scripts/seed_careers.py
~/.venvs/mentora-backend/bin/python scripts/seed_questions.py
```

Optional, for a demo-ready account (Phase 9):
```bash
~/.venvs/mentora-backend/bin/python scripts/seed_demo_account.py
```

## 4. Build the RAG vector store (first time only, or after editing content)

```bash
cd backend
~/.venvs/mentora-backend/bin/python ../rag_pipelines/exam_rag/ingest.py
~/.venvs/mentora-backend/bin/python ../rag_pipelines/career_rag/ingest.py
~/.venvs/mentora-backend/bin/python ../rag_pipelines/interview_rag/ingest.py
```

## 5. Run it

```bash
./scripts/preflight_check.py   # catches port conflicts, missing models, a bad/missing Groq key — before you hit it live
./scripts/start_all.sh         # starts backend + frontend, opens the app at :3000
```

Frontend only (if the backend is already running separately):
```bash
./scripts/start_frontend.sh    # http://localhost:3000
```

## 6. Run the tests

```bash
./scripts/run_all_tests.sh
```

27 backend tests (model wrappers, RAG retrieval, full exam/career/auth flows,
security checks). No Playwright/frontend e2e tests yet — Phases 8-9 skipped
them believing the frontend wasn't wired (it was; see "Current state"
above), so this is genuinely still open, not blocked on anything.

## Project layout

```
backend/            FastAPI app — routers, ml_core/ (Model Manager + 5 model
                     wrappers), rag_core/ (RAG pipeline), tests/
frontend/            Next.js app, wired to the real backend (see above)
datasets/            Scripts that built mentora_data/ (Phase 3)
notebooks/           Colab training notebooks (Phase 4)
scripts/phase5/       Quantization + benchmark scripts
rag_pipelines/        RAG knowledge-base content + ingest scripts (Phase 7)
scripts/              Top-level operational scripts (seed, start, preflight, backup)
docs/phases/          Full phase-by-phase technical history/decisions
```

## More detail

Each phase's doc in `docs/phases/` documents not just the plan but what
actually happened — bugs found, decisions made and why, deviations from the
original plan (e.g. Groq instead of local Ollama in Phase 7). Worth reading
before assuming the plan is what shipped — including Phases 8-9's own
backend-only scope decision, which turned out to rest on a wrong premise;
see `docs/phase10/drift_check.md` for the correction.
