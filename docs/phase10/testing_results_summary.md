# Testing & results — summary for the thesis chapter

Source: `docs/phases/MENTORA_Phase8_Integration_Testing_Performance.md`'s
Definition of Done section, which has the full narrative and reasoning
behind every number below. This file is the condensed, thesis-ready version.

## Testing methodology (the pyramid actually used)

1. **Unit tests** — one model wrapper / RAG retrieval call in isolation
   (Phase 6 §8, Phase 7 §12.1). 10 tests.
2. **Integration tests** — full user-facing flows through the real FastAPI
   app (register → MCQ → submit → dashboard reflects it; CV upload →
   rankings → interview), against a dedicated SQLite test database, never
   production data. 17 tests.
3. **Load/security tests** — Locust concurrency test, auth/upload security
   checks, Groq-failure graceful-degradation checks. 10 tests.

**Total: 37 backend tests, all passing** (`./scripts/run_all_tests.sh`).

**Scope note, worth stating directly in the thesis rather than glossing
over**: end-to-end browser testing (Playwright) and the master plan's
11-point manual UI checklist were not run, because the Next.js frontend
has no real API wiring to this backend yet — confirmed by grep, no
`fetch`/`axios` calls anywhere in `frontend/`. Running either would have
tested nothing real. This is an explicit, acknowledged scope boundary, not
an oversight.

## Load testing (Locust, 5 simulated users, 90s)

- **0% failure rate** across all requests.
- `/exam/mcq` (M2, the local FLAN-T5 question generator, serialized behind
  a semaphore shared with M1/M5) showed real queuing under concurrency: one
  call took 34.7s, a second one that queued behind it took 63.1s. This is
  the serialization mechanism working as designed, not a bug — but it's a
  genuine number worth citing when discussing demo/UX implications of the
  RAM-driven design choice to serialize heavy inference.
- `/exam/topic-explainer` (Groq-backed RAG, deliberately NOT behind that
  semaphore — see "why RAG isn't serialized" below) stayed under 2.6s
  throughout, unaffected by M2's load.

## RAM — estimated (master plan §12) vs. measured (Phase 8, real numbers)

| State | Estimated (master plan, pre-implementation) | Measured (Phase 8, live server) |
|---|---|---|
| Idle (M3/M4 resident) | ~3.5-4GB | 1.03GB |
| Peak, one on-demand model loaded | ~4.5-5GB | M1: 1.54GB · M2: 2.49GB · M5: 2.63GB |
| Peak, two heavy models loaded together | not separately estimated | M1+M2: 3.15GB (measured) |

The measured numbers are well under the original estimate across the
board — partly because the original estimate assumed Postgres + a running
Next.js server in the same RAM budget, which this measurement (backend
alone) doesn't include, and partly because Phase 5's fp16 casting (737MB→
369MB for M1, 2.95GB→1.57GB for M2) directly reduced the on-demand
models' footprint versus the FP32 numbers the original estimate implicitly
assumed.

**A real bug found during this measurement, not before**: `unload()`
dropping a model's last Python reference did not actually shrink process
RSS — confirmed in isolation (921MB loaded → 718MB after `unload()` +
`gc.collect()`, nowhere near the ~287MB pre-load baseline). Root cause:
glibc's malloc doesn't return freed memory arenas to the OS on its own.
Fixed by calling `malloc_trim(0)` after `gc.collect()` on every idle-unload
(`backend/ml_core/memory_watchdog.py`). Measured full recovery for M1 in
the live server (1542MB → 1037MB, back to baseline); partial/session-
dependent recovery for M2 due to heap fragmentation from other interleaved
allocations in a busier process — documented honestly as a known
limitation of this technique rather than claimed as a universal fix.

## Security checklist (Phase 8 §8)

| Check | Result |
|---|---|
| SQL injection | Reviewed every `.execute()`/`.format()` call site. One raw f-string DDL site (a schema-migration helper) is safe — its inputs come from hardcoded SQLAlchemy model definitions, never request data. Everything else uses parameterized SQLAlchemy Core queries. No injection vector found. |
| Password storage | bcrypt confirmed, with a dedicated test asserting the stored value is never the plaintext password. |
| JWT expiry | Tested directly — a token re-signed with a past `exp` is rejected with 401. |
| CORS | `cors_origins` is the actual frontend origin, never `["*"]`. |
| File upload validation | **Found missing, then fixed.** No size limit or content check existed — a renamed `.exe` would have silently been processed as garbage text. Added a 5MB cap and magic-byte sniffing (real file-format signatures, not just the filename extension). 4 tests, including uploading an actual `.exe` renamed to `.pdf` and confirming rejection. |
| Rate limiting | **Found missing, then fixed.** No limiting existed on `/auth/login` or `/auth/register` — added via `slowapi` (5/min login, 10/min register). Tested against the real mechanism, not mocked. |
| Automated scan (OWASP ZAP) | Not run — optional per the testing plan, and a full scan needs a long-lived target server beyond this testing pass's scope. |

## Latency profiling

`py-spy` could not be used on the development machine (its OS-level
`ptrace_scope` setting blocks attach without an interactive sudo password).
Used Python's built-in `cProfile` on the CV-upload/NER request path
instead: 95% of the 1.36s request time is `torch._C._nn.linear` — the BERT
model's own forward-pass matrix multiplications across its layers. No
measurable time lost to tokenization, text chunking, or the BIO-decoding
logic around it — the latency is the model's real compute cost, not an
inefficiency in the code wrapping it.
