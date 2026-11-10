# Documentation-vs-implementation drift check (§2.2)

## Data model (ERD)

```bash
grep -E "^class \w+\(Base\)" backend/database/models.py
```

Real tables (13): `User`, `StudentIntelligenceProfile`, `ExamSession`,
`Question`, `SessionAnswer`, `TopicScore`, `CareerProfile`,
`CareerRanking`, `Roadmap`, `CvUpload`, `InterviewSession`, `InterviewQa`,
`Notification`.

Cross-referenced against the master plan's ERD list (§4):
`USERS` · `STUDENT_INTELLIGENCE_PROFILE` · `EXAM_SESSIONS` ·
`SESSION_ANSWERS` · `QUESTIONS` · `TOPIC_SCORES` · `CAREER_PROFILES` ·
`CAREER_RANKINGS` · `ROADMAPS` · `CV_UPLOADS` · `INTERVIEW_SESSIONS` ·
`INTERVIEW_QA` · `NOTIFICATIONS`.

**Result: exact match, no drift.** All 13 entities present on both sides,
no extra tables on either side.

## The one real drift found: §5 (model deployment strategy)

The master plan's §5 table (model list) says M1/M2/M5's "Local runtime"
is "ONNX + ONNX Runtime dynamic quant" — the originally planned approach.
**This never shipped.** What actually runs in production is native
float16 casting (`backend/ml_core/models/*.py` load `model_quantized.pt`
files produced by `scripts/phase5/quantize_m{1,2,5}.py`, which cast to
fp16 — no ONNX export step exists anywhere in the actual codebase).

Two real pivots happened, in order:
1. The original plan assumed the target CPU might lack AVX2 (requiring
   the ONNX detour to avoid PyTorch's FBGEMM quantization backend
   crashing). Checking the actual target laptop found AVX2 **is**
   present, removing the need for ONNX before any of it was built.
2. The now-simpler plan — `torch.quantization.quantize_dynamic` directly —
   was then found to produce degenerate (not just lossy) output, traced
   to a broken/deprecated backend in this specific torch version, not an
   AVX2 or architecture issue. Fixed by switching to float16 casting.

Full story: `docs/phase10/hardware_adaptation_story.md`.

**Documentation updated to match reality, not the other way around**: see
`scripts/phase5/README.md` (written during Phase 5, documents the actual
investigation) and this file + the hardware-adaptation story (written
during Phase 10, consolidate it for the thesis). The master plan document
itself (`docs/phases/MENTORA_Complete_Project_Plan.md`) is left as-is
rather than edited — it's the original plan, a valid historical artifact
showing what was intended before implementation revealed the real
constraints; the phase-specific docs (Phase 5, this Phase 10 set) are
where the "what actually happened" record lives.

## Other sections checked

- **RAG system (§6)**: master plan assumes local Ollama. Actual
  implementation uses Groq (cloud) — a deliberate, disclosed Phase 7
  pivot, documented in that phase's doc header and `docs/phase10/
  viva_question_bank.md`'s "why Groq" answer. Same pattern as the
  quantization drift: plan documented as the plan, deviation documented
  separately with reasoning, not silently merged into looking like the
  original plan all along.
- **API endpoint reference (§10 of the master plan)**: superseded by the
  live, auto-generated `docs/openapi.json` (exported from the real
  running app, §2.3) — more reliable than cross-checking a hand-written
  table that can drift the moment an endpoint changes.

## A documentation error, not just plan-vs-reality drift (2026-11-10)

Unlike the drift above — plan says one thing, reality correctly did
another, both honestly recorded — this one is a factual error that
propagated across three artifacts: Phase 2 (2026-09-18) wired the Next.js
frontend to a mock backend end to end, closing with its own §8 click-through
checklist. Phase 6's and Phase 8's docs then stated, as settled fact, that
the frontend had "no real wiring" / "no `fetch`/`axios` calls anywhere" —
never re-verified, just carried forward — and Phase 9 repeated it,
commenting out `start_all.sh`'s frontend line and skipping its own UI-polish
item on that basis.

**What was actually true**: the wiring existed throughout, built against
Phase 2's *mock* response shapes. Phases 6-7 then changed several real
endpoint shapes (`/career/cv-upload`'s `projects`→`degrees`, `/career/
ai-suggest`'s response shape, `/interview/start`'s now-required
`career_goal` param, `/interview/{id}/ask`'s combined `answer` field
replacing separate `ai_feedback`/`next_question`) without the frontend
being revisited — so the frontend was simultaneously "wired" and
increasingly broken against the real backend, which is why the "unwired"
claim went unquestioned for three phases: nobody who believed it had a
reason to go click through the UI and find otherwise.

**Found by**: re-running the Phase 6 claim's own grep during a Phase 2
re-audit (`grep -rl "apiFetch\|fetch(" app/ components/ lib/`) turned up
~15 files, not zero. A full live-browser audit against the running backend
then found and fixed 8 real bugs (stuck-loading `Promise.all` gating,
3 crash/422 bugs, 2 response-shape mismatches, 2 missing error/refresh
cases) — see that commit's message for the itemized list.

**Fixed**: `frontend/lib/types.ts` and the affected pages; `README.md`,
`frontend/README.md`, `scripts/start_all.sh`, `scripts/start_frontend.sh`
(frontend launch uncommented); correction notes added in place in Phase
8's and Phase 9's docs next to the original false claims, which are left
otherwise unedited for the historical record — same philosophy as the
quantization and RAG drift above, extended to "a stated fact turned out to
be wrong," not just "the plan changed."
