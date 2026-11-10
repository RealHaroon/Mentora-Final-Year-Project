# Mentora Backend

FastAPI backend. Real, database-backed auth (`/auth/*`, `/users/me`) per the
Phase 1 milestone in `docs/phases/MENTORA_Complete_Project_Plan.md` §11.

`exam`, `career`, `dashboard`, and `interview` are now real too, not mock:
the 5 trained models are wired through `ml_core/`'s Model Manager (Phase 6),
and the RAG chatbot (`rag_core/`, Groq + ChromaDB) backs the topic-explainer/
career-Q&A/mock-interview endpoints (Phase 7). `learning` and
`notifications`, and a few sub-endpoints within `exam`/`dashboard`
(`/exam/timetable`, `/exam/today-topic`, `/dashboard/stats`,
`/dashboard/score-trend`, `/dashboard/weekly-snapshot`), are still Phase 2's
mock JSON — see each phase's doc in `docs/phases/` for exactly what's real
vs. mock and why.

See the top-level `README.md` for full setup (venv, `.env`, seeding, model/
vector-store artifacts). This file keeps only backend-specific detail.

## Setup

**Important:** this project lives on a drive mounted at a path containing a
colon (`Local Disk (D:)`), and Python's `venv` module refuses to create a
virtualenv inside any path containing `:` (same reason `npm run dev` needed a
workaround in `frontend/` — a colon inside `PATH` corrupts it). So the
virtualenv lives outside the project, in the home directory:

```bash
python3 -m venv ~/.venvs/mentora-backend
~/.venvs/mentora-backend/bin/pip install -r requirements.txt
```

Copy `.env.example` to `.env` and adjust if needed (SQLite works out of the
box, no setup required):

```bash
cp .env.example .env
```

## Running

```bash
~/.venvs/mentora-backend/bin/uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for the interactive Swagger UI. Tables are
created automatically on startup (SQLite file `backend/mentora.db`).

## Switching to PostgreSQL later

No code changes needed — just point `DATABASE_URL` in `.env` at a Postgres
instance:

```
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/mentora_db
```

(and `pip install psycopg2-binary` into the venv first).
