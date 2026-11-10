# Model results — targets vs. achieved

Pulled directly from `notebooks/experiment_log.md` (the live training log kept
during Phase 4), not reconstructed from memory. Drop this table into the
thesis's Model Results / Testing chapter.

| Model | Target metric | Target value | Achieved (final) | Met target? |
|---|---|---|---|---|
| M1 — Gap Classifier | F1 (micro) | ≥ 0.85 | 0.4691 micro / 0.4412 macro | No |
| M2 — Question Generator | BLEU-4 / ROUGE-L | ≥ 0.35 / ≥ 0.50 | 12.13 (sacrebleu 0-100 scale, ≈0.121 on 0-1) / 0.172 | No |
| M3 — Trajectory Predictor | MAE | ≤ 5 | ~5.7-5.9 (varies run to run) | No (close) |
| M4 — Career Matcher | Precision@5 | ≥ 0.75 | 0.779 | **Yes** |
| M5 — CV NER Extractor | Entity F1 | ≥ 0.82 | 0.9497 | **Yes** (on auto-tagged gold set — see caveat below) |

## Honest notes per model (for the "if any model missed its target" section)

**M1 (0.4691 vs. 0.85 target).** Root cause is the training label quality,
not the architecture or hyperparameters: topics were assigned by a keyword
heuristic (`datasets/m1_gap_classifier/tag_topics.py`), not hand-labeled,
and 67% of rows initially fell back to a generic "General &lt;Subject&gt;"
bucket. Attempt 3 (final, 20-class after merging rare classes + class-
weighted loss) nearly doubled macro F1 over attempt 1 (0.26 → 0.44),
confirming the model and training setup are working correctly — the
ceiling is the label quality. A zero-shot retagging attempt
(`retag_m1_zeroshot.ipynb`, bart-large-mnli) was tried and explicitly
rejected before retraining: at any confidence threshold safe enough to
avoid introducing a new bias (over-predicting "Mechanics" for Physics),
only ~8% of "General" rows actually improved, and 10 classes stayed under
the 25-example floor needed for the model to learn them at all. **What
would close the gap**: hand-corrected topic labels on the question bank —
explicitly out of scope for this project's timeline, not a modeling fix.

**M2 (12.13 / 0.172 vs. 35 / 50 target).** This number has real history
behind it worth including in the thesis as evidence of debugging rigor:
attempts 1-2 weren't real training runs at all — `training_loss` stuck at
exactly 0.0 and `eval_loss` was `NaN`, traced to two independent, stacked
bugs (label padding never masked to -100, then T5's own documented fp16
numerical instability). Attempt 3 fixed both — loss became real and
non-degenerate — but BLEU/ROUGE were *still* near-zero, traced to a third,
separate bug: eval-time `.generate()` defaulting to `max_length=21`,
truncating every prediction against a 256-token target regardless of
model quality. Attempt 4, with all three bugs fixed, is the first number
that reflects real model/data quality rather than a bug artifact — missing
the target by about 65%, which is a genuine quality gap (likely the
FLAN-T5+LoRA setup needing more adapter capacity or epochs, or the
question bank's own OCR noise — see `scripts/phase5/README.md`'s
recommendations), not a measurement artifact.

**M3 (~5.7-5.9, target ≤5).** The single most informative finding from
this model's whole training history: re-running attempt 1's *exact*
hyperparameters (attempt 4) produced a different result (5.879 vs. 5.689)
purely because no random seed had been set — meaning the entire 5.69-5.98
spread across 4 attempts, including two deliberate architecture changes
(bigger/deeper LSTM, longer input sequence), is dominated by run-to-run
noise, not real architectural differences. This was confirmed again later
(Phase 9) with a systematic test: the trained model's next-step
predictions run *opposite* to the visible trend on 9/10 hand-constructed
monotonic sequences — consistent with the model having learned
mean-reversion from training data with no real persistent trend, i.e. an
irreducible noise floor in the synthetic data generator
(`datasets/m3_trajectory/generate_synthetic.py`), not an optimization or
architecture problem. `torch.manual_seed(42)` was added and the smallest/
simplest config (attempt 1's) kept as final, since none of the larger
configs beat it.

**M5 (0.9497, exceeds 0.82 target — caveat).** This number is measured on
the *auto-tagged* gold test split (produced by the same spaCy
`PhraseMatcher` pipeline that labeled the training data —
`datasets/m5_cv_ner/build_ner_dataset.py`), not a manually-reviewed gold
set. A manual review pass of the gold split was planned
(`mentora_data/labeled/m5/gold_review.csv` exists for this) but not
completed before this project's later phases proceeded — worth stating
plainly as a caveat on this specific number rather than presenting 0.9497
as fully independently verified.
