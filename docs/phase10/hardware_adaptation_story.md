# The hardware-adaptation story (corrected)

**Note for whoever drops this into the thesis**: the Phase 10 planning doc's
§5 describes an ONNX/AVX2 story that was planned but never actually
happened in this project — it was superseded before implementation (see
Phase 5's doc title: "Updated — AVX2 confirmed present on the target
laptop; ONNX Runtime detour removed"). The real story below is richer: the
AVX2 concern *was* resolved early, but a second, unexpected problem showed
up right where the simplified plan assumed smooth sailing. Use this
version, not the original plan's.

## Problem statement

Deploying 5 transformer-based models (DeBERTa, FLAN-T5-Large+LoRA, an
LSTM, Sentence-Transformers, BERT) on the actual target machine — 8GB RAM,
no GPU, no Docker — with two of the five needing active quantization to
fit the RAM budget on-demand. The original master plan assumed the target
CPU might lack AVX2, which PyTorch's default quantization backend
(FBGEMM) requires, and planned an ONNX Runtime detour to avoid that risk.

## Investigation #1 — the assumed risk didn't materialize

Before implementing the ONNX detour, `cat /proc/cpuinfo | grep flags | grep
-o avx2` on the actual target laptop confirmed AVX2 **is** present. This
removed the need for ONNX entirely — `torch.quantization.quantize_dynamic()`
could be used directly, with no export step and no extra dependency. Phase
5 proceeded on this simpler plan.

## Investigation #2 — the real, unexpected problem

Running that direct INT8 dynamic quantization on M1 (DeBERTa) and checking
its output against the original FP32 model on real validation
examples — a step taken specifically *because* "never trust a quantization
technique without a real-example parity check" was already the working
principle, not skipped as a formality — revealed something far worse than
ordinary INT8 lossiness: the quantized model's output was **degenerate**,
collapsing to a near-constant narrow range regardless of input (max
logit diff ~5.5 on a model whose real FP32 logits span roughly -3 to +3;
20/20 real test questions produced a *different* predicted label set
between FP32 and quantized).

Rather than assume this was a DeBERTa-specific numerical-sensitivity quirk,
the same technique was tested on M5 (BERT) — and failed the same way, with
a tell that ruled out ordinary noise entirely: the max-diff value was
**identical to 13 decimal places** across 5 different real resume inputs.
Identical output regardless of input is the signature of a broken
computation, not lossy-but-working compression. The root cause traced to
the installed environment itself: `torch.ao.quantization` (the legacy
codepath `quantize_dynamic` uses) is flagged deprecated in its own runtime
warnings on this torch version — consistent with a backend bug specific to
this software environment, not a property of either model architecture.

## Solution

Switched from INT8 dynamic quantization to native float16 casting
(`model.to(dtype=torch.float16)`) — a simpler, non-deprecated path. Trade
4x compression for 2x, but for output that's actually trustworthy.

## Verification

The same real-example parity-checking discipline that caught the INT8 bug
was applied to confirm the fp16 fix, model-appropriately: predicted
multi-label sets for M1 (0/20 mismatches vs. FP32, max logit diff ~0.005 —
down from ~5.5 on the broken INT8 path on the identical inputs), per-token
tag sequences for M5's NER output, and generated-text JSON validity for
M2. A separate local smoke test then confirmed the saved files actually
load and run from disk on the real target machine (not just the in-memory
object from the same script that created them) — catching a different
risk class entirely (pickle/torch-version drift between save and load
environments). Phase 8 later re-confirmed the resulting RAM/latency
numbers hold up inside the actual running FastAPI backend under load, not
just in a one-off benchmarking script.

## Outcome and the broader, generalizable lesson

The concrete outcome: a fully local (no Docker, no GPU) deployment of 5
transformer-based models within an 8GB RAM budget, verified correct and
verified fast enough, on real consumer hardware rather than a
cloud/GPU development machine.

The broader lesson generalizes past this one project: a standard,
well-documented quantization technique failing is not automatically a
hardware limitation, even when the hardware genuinely is constrained — it
can be a software/environment bug masquerading as one, as it was here.
"The library ran without an error" and "the library produced correct
output in this specific environment" are different claims, and only a
real-example parity check (not a smoke test that just confirms the code
runs) distinguishes them. This is a directly reusable discipline for
deploying any ML model to resource-constrained hardware, independent of
which specific quantization library or technique is involved.
