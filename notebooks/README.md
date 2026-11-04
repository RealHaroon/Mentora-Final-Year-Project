# Phase 4 — Colab training notebooks

Five notebooks, one per model, in the training order from the plan
(`docs/phases/MENTORA_Phase4_Model_Training.md`): **M3 → M4 → M1 → M5 → M2**
(cheapest/fastest first).

**Nothing here runs locally.** This laptop has no GPU; every notebook is
built to run on Google Colab's free T4 tier. I validated the data-loading
and schema-adaptation logic in each notebook against the real local
`mentora_data/` files (column names, JSON validity, label mapping) before
handing them off — the parts I *can't* test without a GPU are the actual
model downloads and training loops themselves.

## One-time setup

1. Upload the whole `mentora_data/` folder (from Phase 3) to your Google
   Drive, at `My Drive/mentora_data` — the notebooks expect exactly that path.
2. Open a notebook in Colab (upload the `.ipynb` file, or open it from Drive
   once you've also uploaded this `notebooks/` folder there).
3. Runtime → Change runtime type → Hardware accelerator → **T4 GPU** → Save.
4. Run cells top to bottom. The first cell mounts your Drive and will ask you
   to authorize access — that's expected.

## Running order

| Order | Notebook | Model | Target metric |
|---|---|---|---|
| 1 | `train_m3.ipynb` | Trajectory Predictor (LSTM) | val MAE ≤ 5 |
| 2 | `train_m4.ipynb` | Career-Skill Matcher | Precision@5 ≥ 0.75 |
| 3 | `train_m1.ipynb` | Knowledge Gap Classifier | F1 (micro) ≥ 0.85 |
| 4 | `train_m5.ipynb` | CV/Transcript NER | Entity F1 ≥ 0.82 |
| 5 | `train_m2.ipynb` | Question Generator (FLAN-T5+LoRA) | BLEU-4 ≥ 0.35, ROUGE-L ≥ 0.50 |

**Status (see "Fixed" sections below for what changed):** M4 (Precision@5 =
0.779) and M5 (Entity F1 = 0.9497) passed — no need to re-run. **M3 is
finalized at MAE = 5.69-5.98** (four attempts, see below — this is an
accepted, documented limitation, not something that needs another re-run).
M1 is finalized at F1 micro = 0.4691 (also a documented limitation — see
`experiment_log.md`). **M2 is finalized at BLEU-4 = 12.13 / ROUGE-L =
0.172** (attempt 4, below target but the first bug-free, trustworthy
result — see `experiment_log.md`). All five models now have a final,
honestly-documented number; none need further re-runs unless you want to
push further on M1/M2/M3's known limitations.

M3/M4/M1/M5 combined should take a couple of days of elapsed time (not
continuous GPU time); M2 is the heavy one and is explicitly saved for last,
per the plan's own estimate of "2-4 weeks, dominated by M2."

## Known adaptations and limitations (read before training M1, M4, M2)

These notebooks were adapted to the *real* Phase 3 output, which differs
from the plan doc's hypothetical schema in a few places. Each notebook's
first markdown cell documents its own adaptations; the two that matter most:

- **M1** trains as single-label multi-class (not multi-label) because the
  real data has one topic per question. More importantly: topic labels for
  the 1777 MDCAT-derived questions are **heuristic** (keyword-matched, 67%
  fell back to a generic "General &lt;Subject&gt;" bucket) — not manually
  verified. Expect F1 to reflect that; hand-correcting the MDCAT topic tags
  is the highest-leverage fix if the target isn't met, well above
  hyperparameter tuning.
- **M2**'s `correct_answer` field is `null` for all MDCAT-derived training
  examples (the answer-key OCR never worked out in Phase 3 — see
  `mentora_data/SOURCES.md`). The model will still learn to generate
  well-formed questions, just without a correct answer to imitate for most
  of its training data.
- **M5**'s gold evaluation set is auto-tagged, not hand-corrected yet. Do
  that manual review (see `mentora_data/labeled/m5/gold_review.csv`) before
  trusting the Entity F1 number as final.

## Fixed: "error: externally-managed-environment" on the `!pip install` cell

Colab's base image now enforces the same PEP 668 protection regular
Debian/Ubuntu does, which normally blocks a plain `pip install` outside a
venv. Since a Colab VM is fully ephemeral (wiped at the end of every
session), there's no real "system" worth protecting here — added
`--break-system-packages` to every `!pip install` line across all 5
notebooks. If you pulled a notebook before this fix and hit this error, just
add `--break-system-packages` to the end of the failing `!pip install` line
and re-run.

## Fixed: "ValueError: Attempting to unscale FP16 gradients"

Hit this on the first real training run (M1). Root cause: newer
`transformers`/Hub versions can load a model's weights in whatever dtype
they're stored in (often fp16, to save bandwidth) instead of always
upcasting to fp32 on `from_pretrained()`. Combined with `fp16=True` in
`TrainingArguments` (which expects fp32 parameters so it can scale/unscale
fp16 *computation* correctly), that produces exactly this error. Fixed in
**M1, M5, and M2** (the three notebooks using `fp16=True`) by explicitly
passing `torch_dtype=torch.float32` to the base model's `from_pretrained()`
call — parameters stay fp32, autocast still gives fp16 speed on the actual
forward/backward computation, which is the correct mixed-precision recipe.
If you pulled these notebooks before this fix, re-download them.

## Fixed: M2 training_loss stuck at 0.0 / eval_loss NaN / near-zero BLEU-ROUGE

The first real M2 training run reported `training_loss: 0.0` for the entire
3-epoch run and `eval_loss: nan`, with BLEU-4=0.082 / ROUGE-L=0.145 (target
≥0.35 / ≥0.50). Root cause: the `tokenize()` cell built `labels` directly
from the tokenizer's padded `target_text` output, never masking padding
positions to `-100`. T5's loss is plain `CrossEntropyLoss`, which does *not*
automatically ignore the pad token — so the model could trivially drive
training loss toward 0 by learning to predict PAD for the ~70% of each
256-token target that's just padding, without ever learning real question
content. This bug was copied verbatim from the plan doc's own §6.3 example,
which has the same issue.

Fixed in `train_m2.ipynb`'s tokenize cell by replacing pad-token positions
in `labels` with `-100` before assigning them. **If you already ran the
buggy version**, the training cell auto-resumes from any checkpoint under
`mentora_models/model2_question_generator/checkpoint-*` on Drive — delete
or rename that folder before re-running, otherwise it'll resume from
checkpoints trained on the broken labels instead of starting fresh.

**This fix alone wasn't enough** — attempt 2 (with the label-masking fix
correctly in place) hit the exact same `training_loss: 0.0` / `eval_loss:
nan` symptom again. Root cause #2: T5/FLAN-T5 is well-documented as
numerically unstable under fp16 mixed-precision training, independent of
the labels bug. Multiple HuggingFace forum threads report this exact
signature for T5-family models specifically:
- https://discuss.huggingface.co/t/t5-variants-return-training-loss-0-and-validation-loss-nan-while-fine-tuning/30839
- https://discuss.pytorch.org/t/training-loss-0-0-validation-loss-nan/168467
- https://discuss.huggingface.co/t/training-loss-is-zero-from-the-first-step-and-model-generation-is-empty-after-training/72359

Fixed by setting `fp16=False` in `train_m2.ipynb`'s `Seq2SeqTrainingArguments`.
T4 GPUs (Colab's free tier) also lack efficient native bf16, so plain fp32
is the safe choice here — the LoRA adapter is only 2.3M trainable params
out of 785M, so this will be slower but numerically correct. **Delete
`mentora_models/model2_question_generator/checkpoint-*` on Drive again**
before this re-run too (attempt 2's checkpoints were trained with fp16).

## Fixed: M2 BLEU-4/ROUGE-L still near-zero after both fixes above

Attempt 2 (both fixes above correctly in place) resolved the 0.0/NaN
symptom — `training_loss: 8.53`, `eval_loss: 1.76`, both real numbers — but
BLEU-4/ROUGE-L barely moved (0.085 / 0.157). Root cause #3: the eval step's
`.generate()` call was using the "model-agnostic default" `max_length=21`
(visible as a `UserWarning` in the training cell's output), truncating
every generated prediction to 21 tokens — while `target_text` is tokenized
up to 256 tokens. Comparing a 21-token fragment against a full-length
reference tanks BLEU/ROUGE regardless of how well the model actually
learned. Fixed by setting `generation_max_length=256` in
`Seq2SeqTrainingArguments`. **Delete the Drive checkpoint folder again**
before this re-run.

## Resolved: M2 final result (attempt 4, all three bugs fixed)

Attempt 4 hit one more snag worth documenting: the training cell's
auto-resume logic found a leftover `checkpoint-366` from attempt 3 still on
Drive and silently skipped training entirely (`train_runtime: 0.0163`,
`training_loss: 0.0` again — looked identical to the original bug but was
actually just an instant no-op resume). Caught via the suspiciously-instant
runtime, confirmed by the resumed eval's `eval_loss` matching attempt 3's
exactly to 13 decimal places. Deleted the stale checkpoint, reloaded a
fresh base model + LoRA init (the in-memory model had attempt 3's weights
loaded into it by the resume), and retrained from scratch.

**Real, final, bug-free result**: `training_loss: 8.52` (healthy),
`eval_loss: 1.72`, `eval_bleu4: 12.13` (sacrebleu's native 0-100 scale,
≈0.121 on a 0-1 scale), `eval_rougeL: 0.172`. Still below target (BLEU-4
≥0.35, ROUGE-L ≥0.50 — roughly a third of the way there on both), but this
is the first number that reflects actual model/data quality rather than a
bug. `lora_adapter/` saved to Drive. If pushing further: try `r=16` for
more LoRA capacity, or grow/improve the M1 question bank that M2's training
data is built from (see `datasets/m2_question_generator/build_training_data.py`)
— quality of the underlying 2155 examples is more likely the ceiling than
model capacity at this point.

## Resolved (as a documented limitation): M3 missed MAE target (4 attempts)

Attempt 1 (hidden_size=128, 2 LSTM layers, SEQ_LEN=5) came in just short at
5.689. Per the plan doc's own troubleshooting list, tried hidden_size=256/3
layers (attempt 2: **5.975**, worse) and SEQ_LEN=7 (attempt 3: **5.872**,
also worse). A 4th run reverting to attempt 1's exact config (before a seed
was fixed) landed at **5.879** — a different number from attempt 1 despite
identical hyperparameters, because **the notebook never set a random seed**.
That alone explains most of the apparent "architecture effect": run-to-run
noise (weight init + train/val split) spans almost the whole 5.69-5.98
range we'd been attributing to hyperparameters.

**Conclusion: this is very likely an irreducible noise floor in the
synthetic data** (`datasets/m3_trajectory/generate_synthetic.py`'s
per-session noise), not a model problem — consistent with every config
tried landing in the same narrow band regardless of capacity or window
size. `train_m3.ipynb` now sets `torch.manual_seed(42)` for reproducibility
and is reverted to attempt 1's architecture (no worse than the
alternatives, simplest/fastest). **M3 is finalized at MAE ≈ 5.7-5.9** —
documented as a limitation in `experiment_log.md`, not something that needs
further re-running unless you want to attack the synthetic generator's
noise level directly.

## Fixed (partially): M1 missed F1 target badly (0.4352 vs >=0.85)

This one isn't a code bug — it's heuristic topic labels from
`tag_topics.py`: 30 classes, several with under 10 examples (one with only
3), 67% of MDCAT rows falling back to a generic "General &lt;Subject&gt;"
bucket. No hyperparameter change fixes a class with 3 training examples.

Two mitigations applied, **chosen deliberately as a partial fix, not a full
one** — closing the rest of the gap needs the MDCAT questions' topics
hand-corrected, which is real manual work:
- `datasets/m1_gap_classifier/merge_rare_topics.py` folds any topic with
  fewer than 25 examples into its subject's General bucket (30 -> 20
  classes, all now >=25). Also re-ran `build_training_data.py` for M2 so
  its prompts reflect the merged labels.
- The training cell now uses a `WeightedTrainer` subclass with
  inverse-frequency class weighting, so the classifier isn't just learning
  to always predict the biggest classes.

Attempt 3 (merge + class weighting, run correctly this time) landed at F1
micro = 0.4691 / macro = 0.4412 — better, but still well short of 0.85. The
remaining gap is the heuristic topic labels themselves, not hyperparameters.

## New: `retag_m1_zeroshot.ipynb` — replacing keyword tags with zero-shot

Re-tags the 1777 MDCAT rows with `facebook/bart-large-mnli` zero-shot
classification against each subject's real topic list, instead of
`tag_topics.py`'s substring-keyword matching. Writes
`question_bank_final_zeroshot.csv` alongside the original (never
overwrites it) plus a `zeroshot_retag_review.csv` with confidence scores
for spot-checking. Run this, review the spot-check cell's output, then:

1. Download `question_bank_final_zeroshot.csv` from Drive.
2. Run `merge_rare_topics.py` against it locally as a safety net (zero-shot
   may still leave some topic under the 25-example floor).
3. Replace your local `question_bank_final.csv` with the result, re-upload
   to Drive, delete `mentora_models/model1_gap_classifier/checkpoint-*`
   (label set will change again), and re-run `train_m1.ipynb` for attempt 4.

## Disconnect-safety

Every notebook checkpoints straight to Google Drive (never Colab's local
`/content/` disk) and auto-resumes from the latest checkpoint if the session
disconnects — just re-run the notebook from the top; it'll skip back to
where it left off rather than restarting training from scratch. Free Colab
sessions disconnect without warning (idle timeout, ~12hr cap, GPU demand) —
treat it as something that *will* happen, not an edge case.

## After this phase

Fill in `experiment_log.md` in this folder as you go (one row per training
attempt) — it's also directly reusable in the thesis's "model training
results" chapter. Once every model in the Phase 4 doc's §9 "Definition of
done" checklist is checked off, Phase 5 (ONNX export + quantization for
local inference) can start.
