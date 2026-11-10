# rag_pipelines/

Content and ingestion for the three RAG knowledge bases (Phase 7):
`exam_rag/`, `career_rag/`, `interview_rag/`. Each has a `content/` folder
of hand-written Markdown documents (with `topic`/`career` + `type`
frontmatter) and an `ingest.py` that chunks and loads them into ChromaDB.

**The actual RAG pipeline code (retrieval + generation) lives in
`backend/rag_core/`, not here** — importing across this top-level/
`backend/` boundary on every request would need the same `sys.path` hack
`ingest.py` uses as a standalone script; the importable code stays in the
package that actually imports it at request time (see
`docs/phases/MENTORA_Phase7_RAG_Pipeline.md`'s Definition of Done for the
full reasoning).

Run ingestion after editing any content (from `backend/`):
```bash
~/.venvs/mentora-backend/bin/python ../rag_pipelines/exam_rag/ingest.py
~/.venvs/mentora-backend/bin/python ../rag_pipelines/career_rag/ingest.py
~/.venvs/mentora-backend/bin/python ../rag_pipelines/interview_rag/ingest.py
```
