# Repository hygiene check (Phase 10 §9)

## Secret scan across full git history

```bash
git log -p --all | grep -iE "SECRET|PASSWORD|API_KEY|gsk_"
```

Run and reviewed line by line. **No real secrets found committed at any
point in history.** What the grep matches, explained:

- Route/function/variable names containing "password" (`forgot_password`,
  `change_password`, `ForgotPasswordRequest`, etc.) — code identifiers,
  not credentials.
- `gsk_totally_invalid_000000000000000000000` — a deliberately fake Groq
  key used in test fixtures (`tests/test_security.py`,
  `tests/test_rag_graceful_degradation.py`) to test failure handling. Not
  a real key.
- `testpass123`, `MentoraDemo2026!` — test/demo fixture passwords for
  local-only accounts (the integration test suite's throwaway users, and
  the Phase 9 demo account). Not real user credentials, not reused
  anywhere external.
- `demo2025` — appears once, inside old Phase 1/2 documentation prose as
  an example curl command from before real auth existed. Historical
  example text, not a live credential.
- `<password>` in `DATABASE_URL=postgresql://postgres:<password>@...` —
  a placeholder token in `.env.example`/docs, never a real connection
  string.
- The real `GROQ_API_KEY` value itself never appears — `backend/.env` has
  always been gitignored, confirmed via `git check-ignore backend/.env`.

## License

`LICENSE` exists at repo root — MIT, correctly filled in (not a
placeholder/template with unfilled `[name]`/`[year]` fields).

## `.gitignore` coverage (cross-checked against what's actually untracked)

Confirmed excluded: `node_modules/`, Python venvs, `.env`, `mentora.db` /
`test_mentora.db`, `mentora_data/` (Phase 3 raw data, licensing), 
`mentora_models/` + `ml_models/` (Phase 4/5 trained weights, ~6GB
combined — too large for git, documented in the top-level `README.md`
how to obtain/regenerate them), `vector_store/` (ChromaDB index,
rebuildable via `rag_pipelines/*/ingest.py`), `backups/` (Phase 9 DB
snapshots — real data, not source), `uploads/` (user-uploaded CVs),
`.pytest_cache/`.

## Not done here (left for the user to decide when ready)

- **Git tag for the final submitted state** (`git tag v1.0-final`) — not
  created, since tagging a specific commit as "the final version" is a
  decision only the user should make, at the point they're actually ready
  to lock in a submission commit, not something to do proactively mid-
  development.
- **Commit history cleanup** — the doc calls this optional
  ("not mandatory, but a clean `git log` reads as more professional").
  Not attempted; rewriting history is a destructive operation this
  session's safety rules don't take on without an explicit, specific
  request for it.
