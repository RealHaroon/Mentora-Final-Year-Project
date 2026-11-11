# Full setup guide — from absolute zero

Distinct from the top-level `README.md` (that's the quick version). This
is the fuller sequence, every `.env` variable explained, and how to
reproduce the ML pipeline from raw data rather than just run the
pre-trained models — useful both as a thesis appendix and as the actual
reference if a supervisor or future maintainer needs to rebuild this
environment.

## 0. Prerequisites

- Python 3.14+ (this project's venvs were built against 3.14.4)
- Node.js (for the frontend — see `frontend/README.md`)
- ~6GB free disk for the trained model artifacts, ~1GB for the vector store

## 1. Clone and venv

This repo lives on a path containing a colon (`Local Disk (D:)`), and
Python's `venv` module refuses to create a virtualenv inside a path
containing `:`. The venv lives outside the repo:

```bash
python3 -m venv ~/.venvs/mentora-backend
~/.venvs/mentora-backend/bin/pip install -r backend/requirements.txt
```

## 2. Every backend `.env` variable

Copy `backend/.env.example` to `backend/.env`, then:

| Variable | What it does | Safe default / example |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./mentora.db` (works out of the box); `postgresql://postgres:<password>@localhost:5432/mentora_db` to switch to Postgres (also `pip install psycopg2-binary`) |
| `JWT_SECRET` | Signs auth tokens | Generate a real one for anything beyond local dev: `openssl rand -hex 32` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_EXPIRES_MINUTES` | Token lifetime | `10080` (7 days) |
| `CORS_ORIGINS` | Allowed frontend origin(s) | `["http://localhost:3000"]` — never `["*"]` |
| `DEBUG` | Mounts `/debug/model-status` when true | `false` for anything resembling production/demo |
| `MODEL1_PATH` .. `MODEL5_PATH` | Where each trained model's files live, relative to `backend/`'s own cwd | `../ml_models/saved/model{1..5}_*` (see step 4 below) |
| `TOPICS_JSON` | M1's ordered topic-label list | `./data/topics.json` (already in the repo) |
| `M5_ID2TAG_JSON` | M5's NER tag-id mapping | `./data/m5_id2tag.json` (already in the repo) |
| `GROQ_API_KEY` | Cloud LLM for the RAG chatbot (Phase 7 — Groq instead of local Ollama) | Free key at console.groq.com/keys. **Use a key dedicated to this project.** |
| `GROQ_MODEL` | Which Groq-hosted model to call | `openai/gpt-oss-120b` — verified empirically (queried the live model list, A/B tested against the smaller variant) rather than assumed; model rosters change, re-verify if this stops working |
| `CHROMA_PATH` | ChromaDB's on-disk index location | `../vector_store` |

## 3. Database

Tables are created automatically on backend startup (`Base.metadata.
create_all`). Seed the reference data:

```bash
cd backend
~/.venvs/mentora-backend/bin/python scripts/seed_careers.py
~/.venvs/mentora-backend/bin/python scripts/seed_questions.py
~/.venvs/mentora-backend/bin/python scripts/seed_demo_account.py   # optional, for a demo-ready account
```

## 4. Get the trained model artifacts

Not in git — `ml_models/saved/` (~2.5GB, what the backend actually loads)
and `mentora_models/` (~3.6GB, Phase 4's raw training outputs) are
gitignored for size. Two ways to get them:

**A. Download** — from this project's Google Drive (ask whoever has
access; see `docs/phases/MENTORA_Phase5_Export_Optimize_UPDATED.md` for
the exact expected folder layout under `ml_models/saved/`).

**B. Regenerate from scratch** (reproduces the full ML pipeline):
1. **Data prep (Phase 3)** — `datasets/m{1..5}_*/` hold the scripts that
   built `mentora_data/` from raw sources. Run `datasets/verify_phase3.py`
   after, to confirm the processed data matches what training expects.
2. **Training (Phase 4)** — `notebooks/train_m{1..5}.ipynb`, run on Google
   Colab (needs GPU for M1/M2/M5). `notebooks/experiment_log.md` has the
   real hyperparameters and results from every attempt, including the
   bugs found and fixed along the way — read it before re-running, it'll
   save re-discovering the same issues (e.g. M2's fp16 training
   instability, M3's missing random seed).
3. **Export/quantization (Phase 5)** — `scripts/phase5/quantize_m{1,2,5}.py`.
   **Important**: these use native float16 casting, not the originally-
   planned `torch.quantization.quantize_dynamic` — that approach is
   broken in this project's environment (see
   `scripts/phase5/README.md` for the full investigation). Don't revert
   to it without re-running the parity checks those scripts include.

## 5. Build the RAG vector store

```bash
cd backend
~/.venvs/mentora-backend/bin/python ../rag_pipelines/exam_rag/ingest.py
~/.venvs/mentora-backend/bin/python ../rag_pipelines/career_rag/ingest.py
~/.venvs/mentora-backend/bin/python ../rag_pipelines/interview_rag/ingest.py
```

## 6. Run

```bash
cd backend && ~/.venvs/mentora-backend/bin/python ../scripts/preflight_check.py
../scripts/start_all.sh
```

## 7. Verify

```bash
./scripts/run_all_tests.sh         # backend tests
cd frontend && npm run test:e2e    # 19 Playwright tests — needs both servers running first
```

## Known gaps, stated plainly rather than discovered by surprise

- The Next.js frontend (`frontend/`) is wired to this backend and calling
  real endpoints throughout (since Phase 2) — a line here previously said
  otherwise; that was wrong. See `docs/phase10/drift_check.md` for the
  root cause and what it corrected.
- M1's F1 (0.47) and M2's BLEU-4/ROUGE-L and M3's MAE are all below their
  original targets — each has a specific, documented root cause and
  mitigation discussion in `docs/phase10/model_results_table.md`, not
  silently missing numbers.
- The RAG chatbot needs internet (Groq), unlike the rest of the app —
  disclosed and handled (a Groq outage degrades to a clear error message,
  not a crash), not hidden.
