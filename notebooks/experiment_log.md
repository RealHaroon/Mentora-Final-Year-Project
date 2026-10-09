# Phase 4 — experiment log

Fill in one row per training attempt. Reusable directly in the thesis's
"model training results — targets vs. achieved" chapter
(`docs/phases/MENTORA_Phase4_Model_Training.md` §7).

| Model | Attempt | Key hyperparams changed | Target metric | Achieved | Notes |
|---|---|---|---|---|---|
| M3 | 1 | hidden_size=128, 2 layers, 30 epochs | MAE ≤ 5 | 5.689 | Missed, close. |
| M3 | 2 (pending) | hidden_size=256, 3 layers, 30 epochs | MAE ≤ 5 | — | Delete old Drive checkpoint first (shape mismatch). |
| M4 | 1 | 4 epochs, r=8 | P@5 ≥ 0.75 | 0.779 | **Passed.** No re-run needed. |
| M1 | 1 | lr=2e-5, 5 epochs, 30 classes | F1 ≥ 0.85 | 0.4352 | Missed badly. Heuristic topic tags (67% "General <Subject>" fallback, classes as small as 3 examples). |
| M1 | 2 | lr=2e-5, 5 epochs, class-weighted loss, **but still 30 classes** | F1 ≥ 0.85 | 0.3117 micro / 0.2596 macro | **Invalid attempt** — ran against the stale, unmerged `question_bank_final.csv` on Drive (merge was done locally, never re-uploaded). Class weighting without the merge hurts micro-F1 (up-weights 3-9-example classes the model can't learn, at the cost of the big classes). Re-upload the merged CSV + delete this run's Drive checkpoint (30-class head) before the real attempt. |
| M1 | 3 | lr=2e-5, 5 epochs, 20 classes (rare merged) + class-weighted loss | F1 ≥ 0.85 | 0.4691 micro / 0.4412 macro | Valid attempt (merged CSV correctly on Drive this time). Improved over attempt 1 (0.4352) and macro F1 nearly doubled (0.26->0.44, weighting is working), but still well short of 0.85. Remaining gap is the heuristic topic labels themselves — needs hand-corrected MDCAT topic tags to close further, not more hyperparameter tuning. |
| M1 | 4 (pending) | same as attempt 3, but topics from `retag_m1_zeroshot.ipynb` (bart-large-mnli) instead of keyword heuristic | F1 ≥ 0.85 | — | Run `retag_m1_zeroshot.ipynb`, review the spot-check, merge any still-rare classes, re-upload to Drive, delete checkpoint, retrain. |
| M5 | 1 | 4 epochs | Entity F1 ≥ 0.82 | 0.9497 | **Passed** (on auto-tagged gold set — still needs the manual gold-review pass per SOURCES.md before this number is fully trustworthy). No re-run needed. |
| M2 | 1 | r=8, 3 epochs | BLEU-4 ≥ 0.35 / ROUGE-L ≥ 0.50 | BLEU-4 0.082 / ROUGE-L 0.145, training_loss 0.0, eval_loss NaN | **Bug, not a real attempt** — `tokenize()` never masked pad tokens to -100 in labels. |
| M2 | 2 (pending) | r=8, 3 epochs, pad-masked labels | BLEU-4 ≥ 0.35 / ROUGE-L ≥ 0.50 | — | Delete old Drive checkpoint first (trained on broken labels). |

## Definition of done (Phase 4 doc §9)

- [ ] M3: `lstm_final.pt` saved, val MAE ≤ 5 logged
- [ ] M4: best-checkpoint Sentence-Transformers folder saved, Precision@5 ≥ 0.75 logged
- [ ] M1: `final/` folder (model + tokenizer) saved, F1 (micro) ≥ 0.85 logged on held-out test
- [ ] M5: `final/` folder saved, Entity F1 ≥ 0.82 logged on the **gold** test split specifically
- [ ] M2: `lora_adapter/` folder saved (adapter only, not merged), BLEU-4 ≥ 0.35 and ROUGE-L ≥ 0.50 logged
- [ ] Every saved artifact lives under `mentora_models/` on Google Drive
