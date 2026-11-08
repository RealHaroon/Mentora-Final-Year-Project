# Phase 5 — export & optimize: what actually happened

The Phase 5 doc (`docs/phases/MENTORA_Phase5_Export_Optimize_UPDATED.md`) calls for
dynamic INT8 quantization (`torch.quantization.quantize_dynamic`) on M1, M2, M5.
That's not what these scripts do, for a reason worth recording.

## Bug: `torch.quantization.quantize_dynamic` (INT8) is broken in this environment

Environment: torch 2.15.0+cpu, Python 3.14.4. The legacy `torch.ao.quantization`
path these functions live in is flagged deprecated in its own warnings
("will be removed in 2.10").

Verified on both M1 (DeBERTa) and M5 (BERT): INT8-quantized output is not
ordinarily-lossy, it's **degenerate** — near-constant logits regardless of input.

- M1: max abs logit diff vs FP32 was ~5.5 on a model whose FP32 logits span
  roughly -3 to +3. 20/20 real questions produced a different predicted label
  set. Bisected layer-by-layer: quantizing *any single* Linear layer alone gives
  a small, expected diff (0.01-0.4); the error compounds across the 12-layer
  model until the output is unusable. Tried `per_channel_dynamic_qconfig`
  (normally improves accuracy) — no better (diff ~3-7). Tried excluding the
  self-attention q/k/v projections from quantization — no better either.
- M5: same symptom, and more tellingly, the **exact same** max-diff value
  (4.1415) repeated across 5 different real resume inputs — a clear signature
  of degenerate/constant output, not input-dependent lossy quantization.

Conclusion: this is a backend bug in this torch build, not a property of these
model architectures. Not pursued further (no need to — see fix below).

## Fix: native float16 casting instead

`AutoModelFor...from_pretrained(dir, dtype=torch.float16)` (or `.half()` on an
already-loaded model). Verified before trusting it:

| Model | FP32 | fp16 | Parity check |
|---|---|---|---|
| M1 | 738MB | 369MB | 0/20 label-set mismatches, max logit diff 0.005 |
| M5 | 436MB | 218MB | 3/15 examples with one isolated tag flip (within the doc's own tolerance) |
| M2 | 2950MB | 1567MB | See below |

2x compression instead of the originally-planned 4x, but actually trustworthy.
All three also passed a from-disk reload + inference smoke test
(`benchmark_and_smoke_test.py`) and are packaged in `ml_models/saved/`.

## M2's parity check: 12/12 invalid JSON on *both* FP32 and fp16

This is not a quantization defect. M2's generation quality was already
documented as a Phase 4 limitation (BLEU-4 12.13, ROUGE-L 0.172 — see
`notebooks/experiment_log.md`, M2 attempt 4). On these 12 sampled prompts,
greedy decoding produces repetitive, malformed text (e.g. "the molecule of a
molecule of a molecule...") on the **original FP32 model**, not just the fp16
one. fp16 reproduces this faithfully — same failure rate, no NaN/Inf, no new
divergence — which is what a parity check is supposed to show when the
quantization step itself isn't the problem.

Practical consequence: the Phase 5 doc's M2 done-criterion ("parity-checked...
with valid-JSON output confirmed") can't be literally satisfied without
improving M2's underlying generation quality, which was already decided
against revisiting (see M1/M2/M3's "stop here, move to Phase 5" decision).
Treating this as a documented, inherited limitation rather than a Phase 5
blocker.

## Files

- `quantize_m1.py`, `quantize_m2.py`, `quantize_m5.py` — load each model,
  cast to fp16, save `model_quantized.pt`, run the parity check described
  above.
- `benchmark_and_smoke_test.py` — Phase 5 §6/§7: fresh load from disk (not the
  in-memory object from the scripts above) + one inference per model, timed,
  for all 5 models including M3/M4 which need no conversion.
