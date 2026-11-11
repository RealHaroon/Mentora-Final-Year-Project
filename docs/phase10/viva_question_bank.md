# Viva/defense question bank

Real questions a panel is likely to ask, with real, specific answers drawn
from this project's own history — not generic ML-interview answers.
Practice explaining the *reasoning* out loud, not a memorized sentence;
the reasoning transfers to follow-up questions, a memorized line doesn't.

---

**Q: Why Next.js over plain React or static HTML?**
httpOnly cookie-based auth is meaningfully more secure against XSS than
storing a JWT in `localStorage`, and that specifically needs a server
component to set the cookie — Next.js's App Router gives that for free
without standing up a separate Node server just for auth.

**Q: Why FastAPI over Django/Flask?**
Native async support, which the Model Manager's design depends on
directly — every blocking model-inference call is routed through
`asyncio.to_thread` so it never blocks the event loop for other requests,
and a semaphore serializes the heavy on-demand models against each other.
That pattern needs a framework built around `async def` routes from the
ground up.

**Q: Why float16 casting instead of standard INT8 dynamic quantization
for M1/M2/M5?**
INT8 dynamic quantization (`torch.quantization.quantize_dynamic`) was
tried first, per the original plan. It produced degenerate output — not
ordinary lossy compression, but near-constant output regardless of input
(verified: 20/20 real test questions produced a different predicted
label set between FP32 and the "quantized" model; the same failure
reproduced on a second, unrelated architecture with a max-diff value
identical to 13 decimal places across different inputs, the signature of
a broken computation, not noise). Traced to the legacy `torch.ao.
quantization` codepath being deprecated and apparently broken in this
specific torch version. Switched to native fp16 casting instead — half
the compression (2x vs. 4x) but verified correct (near-zero diff vs.
FP32 on real examples). Full story: `docs/phase10/hardware_adaptation_story.md`.

**Q: Why LoRA for M2 instead of full fine-tuning?**
FLAN-T5-Large has ~780M parameters; full fine-tuning on Colab's free-tier
GPU VRAM wasn't feasible. LoRA (`r=8, lora_alpha=16`, targeting the
attention `q`/`v` projections) trains only ~2.36M parameters (0.3% of the
model) while still being required to keep the base model as FLAN-T5 per
the project's fixed objectives, not downgrade to a smaller base model.

**Q: Why RAG instead of just prompting the LLM directly for the
mock-interview/topic-explainer chatbot?**
A general-purpose LLM has no reliable specific knowledge of this
platform's actual exam topics or curated interview content — it would
confidently generate plausible-sounding but ungrounded answers. RAG
retrieves the actual curated passages first and instructs the model to
answer only from them, which is directly testable: a deliberately
out-of-scope question (asking the exam-topic chatbot about pizza
toppings) correctly returns "I don't have information on that" instead of
a hallucinated answer — verified live, not assumed.

**Q: Why Groq (a cloud API) instead of local Ollama for the chatbot LLM,
given the whole project is otherwise designed to run fully offline?**
This was a deliberate, disclosed tradeoff, not an oversight. The original
plan assumed local Ollama (`phi4-mini`), but the project's own
documentation already flagged "single-digit tokens/second" as the
realistic expectation on this specific CPU — a 15-30 second wait per
chatbot turn. Groq's hosted inference measured at roughly 1-2 seconds per
call in practice. The explicit call made: working reliably matters more
than being literally offline for this feature. The real cost of that
tradeoff — the chatbot now needs internet, which nothing else in the app
does — was identified and mitigated directly: Groq failures (timeout,
rate limit, outage) are now caught and degrade to a clear "temporarily
unavailable" message instead of crashing the request, verified against a
real API failure, not mocked.

**Q: How do you prevent the app from running out of RAM?**
Three mechanisms, each solving a different part of the problem: (1) only
M3 and M4 stay always-loaded (small/cheap); M1/M2/M5 lazy-load on first
use and auto-unload after 5 minutes idle. (2) A shared semaphore
serializes M1/M2/M5 against each other, so two heavy models can never be
resident and running at once — verified under real concurrent load (two
simultaneous requests measured at essentially the sum of their solo
times, not the max, confirming genuine serialization). (3) A real bug was
found and fixed in the idle-unload itself: dropping a model's Python
reference didn't actually shrink process memory (glibc's allocator holds
onto freed arenas) — fixed with an explicit `malloc_trim(0)` call,
measured to recover RAM in the live server, not just asserted to work.

**Q: How did you validate your models actually work, not just that
they loaded?**
Every quantization/precision change was checked against real validation
examples before being trusted (not just "the code ran without an
exception") — this caught the INT8 bug above. Every model has a real
metrics number from training (F1, BLEU/ROUGE, MAE, Precision@5, entity
F1). Every API endpoint has an integration test exercising the real
Model Manager against a real request, not a mock.

**Q: Why does the trajectory predictor (M3) sometimes seem to predict
scores going the "wrong" direction from what the chart shows?**
This was investigated directly rather than dismissed as noise: 10
hand-constructed monotonic score sequences were run through the real
model, and 9/10 predicted the *opposite* direction from their visible
trend (every ascending sequence predicted "declining," every descending
one predicted "improving"). This is consistent with the model having
learned mean-reversion as its best next-step strategy from training data
with no real persistent trend — a defensible, even sensible thing for a
model to learn if the underlying process genuinely is just noise around a
baseline, which independent evidence (re-running identical hyperparameters
produced a different result purely from an unset random seed) already
suggested was the case for this synthetic training data.

**Q: Why quantize M1/M2/M5 but leave M3 and M4 as plain PyTorch?**
RAM-vs-benefit tradeoff. M3 is a tiny 2-layer LSTM (~1-3MB) — quantizing
it saves nothing meaningful. M4 (Sentence-Transformers) is ~420MB in
FP32, which is cheap enough to keep always-resident outright; quantizing
it would complicate the Sentence-Transformers loading path for a RAM
saving that doesn't change the overall budget much, since it's one model
staying resident either way, not reloaded repeatedly like M1/M2/M5 are.

**Q: M1 landed at F1=0.47 against a 0.85 target — isn't that a
failure?**
It's a real limitation, reported honestly rather than hidden, with a
specific, defensible root cause: the training labels themselves (a
keyword heuristic, not hand-labeled) are the bottleneck, not the model or
training setup — evidenced by macro F1 nearly doubling (0.26→0.44) when
class imbalance was addressed via weighting, showing the model responds
correctly to a real improvement while the label-quality ceiling stays
fixed. A zero-shot relabeling alternative was tried and explicitly
rejected with reasoning (it introduced a new bias and didn't help enough
classes) rather than silently abandoned. What would close the gap — hand-
correcting topic labels — was identified and scoped as future work, not
glossed over.

**Q: What would you do differently with more time or resources?**
Specific, not generic: (1) hand-correct M1's topic labels rather than
rely on the keyword heuristic — this is the identified actual bottleneck,
not more hyperparameter tuning. (2) Complete the manual gold-review pass
on M5's test split before fully trusting its 0.95 F1 number. (3) Try a
higher-rank LoRA adapter or more epochs for M2, and/or clean the question
bank's OCR noise, which likely caps generation quality independent of the
model. (4) Give `/learning-portal`'s backend data (playlist, materials,
watch history) a real per-user DB table — found 2026-11-11 while writing
e2e tests that these are plain module-level Python lists shared across
every account, not scoped per user at all; harmless for a single-demo-
account walkthrough, genuinely wrong for more than one real user. (5) A
local-model fallback path alongside Groq, to restore full offline
capability for the RAG chatbot specifically, now that its cloud
dependency is a known, disclosed tradeoff.

**Q: How thorough was the security review — is this production-ready?**
Explicitly scoped for an FYP, not claimed as production-grade: reviewed
for SQL injection (none found — parameterized queries throughout),
confirmed real bcrypt password hashing, confirmed JWT expiry actually
rejects old tokens, confirmed CORS is scoped to the real frontend origin
not a wildcard, and — found genuinely missing during this pass, then
fixed — added file-upload validation (size cap + real magic-byte
checking, not just trusting the filename extension) and rate limiting on
the auth endpoints. An automated scanner (OWASP ZAP) was not run; that's
disclosed as a scope boundary, not hidden.
