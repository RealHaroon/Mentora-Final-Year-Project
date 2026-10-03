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
