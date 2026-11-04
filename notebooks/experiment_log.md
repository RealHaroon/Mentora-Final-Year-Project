# Phase 4 — experiment log

Fill in one row per training attempt. Reusable directly in the thesis's
"model training results — targets vs. achieved" chapter
(`docs/phases/MENTORA_Phase4_Model_Training.md` §7).

| Model | Attempt | Key hyperparams changed | Target metric | Achieved | Notes |
|---|---|---|---|---|---|
| M3 | 1 | hidden_size=128, 2 layers, SEQ_LEN=5, 30 epochs, no fixed seed | MAE ≤ 5 | 5.689 | Missed, close. |
| M3 | 2 | hidden_size=256, 3 layers, SEQ_LEN=5, 30 epochs, no fixed seed | MAE ≤ 5 | 5.975 | Worse than attempt 1. Also got stuck (val_MAE frozen ~11.84) for the first 9 epochs — bigger/deeper LSTM harder to optimize from scratch. |
| M3 | 3 | hidden_size=128, 2 layers, SEQ_LEN=7, 30 epochs, no fixed seed | MAE ≤ 5 | 5.872 | Also worse than attempt 1. Essentially flat across all 30 epochs (56-58 train_loss range, no real trend) — looked like a noise floor, not an optimization issue. |
| M3 | 4 | hidden_size=128, 2 layers, SEQ_LEN=5, 30 epochs, no fixed seed (attempt 1's exact config, re-run) | MAE ≤ 5 | 5.879 | **Key finding**: identical hyperparameters to attempt 1, different result (5.879 vs 5.689) — confirms no random seed was set, and run-to-run variance alone spans most of the 5.69-5.98 range across all 4 attempts. **M3 FINALIZED**: this is an irreducible noise floor in the synthetic data (`datasets/m3_trajectory/generate_synthetic.py`), not an architecture problem. `train_m3.ipynb` now sets `torch.manual_seed(42)` and reverts to attempt 1's config. No further training needed unless attacking the synthetic generator's noise level directly. |
| M4 | 1 | 4 epochs, r=8 | P@5 ≥ 0.75 | 0.779 | **Passed.** No re-run needed. |
| M1 | 1 | lr=2e-5, 5 epochs, 30 classes | F1 ≥ 0.85 | 0.4352 | Missed badly. Heuristic topic tags (67% "General <Subject>" fallback, classes as small as 3 examples). |
| M1 | 2 | lr=2e-5, 5 epochs, class-weighted loss, **but still 30 classes** | F1 ≥ 0.85 | 0.3117 micro / 0.2596 macro | **Invalid attempt** — ran against the stale, unmerged `question_bank_final.csv` on Drive (merge was done locally, never re-uploaded). Class weighting without the merge hurts micro-F1 (up-weights 3-9-example classes the model can't learn, at the cost of the big classes). Re-upload the merged CSV + delete this run's Drive checkpoint (30-class head) before the real attempt. |
| M1 | 3 | lr=2e-5, 5 epochs, 20 classes (rare merged) + class-weighted loss | F1 ≥ 0.85 | 0.4691 micro / 0.4412 macro | Valid attempt (merged CSV correctly on Drive this time). Improved over attempt 1 (0.4352) and macro F1 nearly doubled (0.26->0.44, weighting is working), but still well short of 0.85. Remaining gap is the heuristic topic labels themselves — needs hand-corrected MDCAT topic tags to close further, not more hyperparameter tuning. |
| M1 | 4 (tried, not adopted) | same as attempt 3, but topics from `retag_m1_zeroshot.ipynb` (bart-large-mnli) instead of keyword heuristic | F1 ≥ 0.85 | n/a | Zero-shot retagging ruled out before retraining — at any confidence threshold safe enough to avoid its Physics "Mechanics" bias, only ~8% of "General" rows actually improved, and 10 classes stayed under the 25-example floor. Not worth the GPU time. **M1 FINALIZED at attempt 3: F1 micro = 0.4691 / macro = 0.4412.** Documented limitation: heuristic MDCAT topic labels, not a code/hyperparameter issue — only hand-correction could close the rest of the gap, decided out of scope for now. |
| M5 | 1 | 4 epochs | Entity F1 ≥ 0.82 | 0.9497 | **Passed** (on auto-tagged gold set — still needs the manual gold-review pass per SOURCES.md before this number is fully trustworthy). No re-run needed. |
| M2 | 1 | r=8, 3 epochs, fp16=True | BLEU-4 ≥ 0.35 / ROUGE-L ≥ 0.50 | BLEU-4 0.082 / ROUGE-L 0.145, training_loss 0.0, eval_loss NaN | **Bug, not a real attempt** — `tokenize()` never masked pad tokens to -100 in labels. |
| M2 | 2 | r=8, 3 epochs, pad-masked labels, fp16=True | BLEU-4 ≥ 0.35 / ROUGE-L ≥ 0.50 | BLEU-4 0.083 / ROUGE-L 0.149, training_loss 0.0, eval_loss NaN | **Still a bug, not a real attempt** — same symptom despite the label fix being correctly in place. Root cause #2: T5/FLAN-T5 is numerically unstable under fp16, independent of the labels bug (see README sources). |
| M2 | 3 | r=8, 3 epochs, pad-masked labels, fp16=False | BLEU-4 ≥ 0.35 / ROUGE-L ≥ 0.50 | BLEU-4 0.085 / ROUGE-L 0.157, training_loss 8.53, eval_loss 1.76 | Loss finally real/non-degenerate (bugs 1+2 confirmed fixed), but BLEU/ROUGE still near-zero. Root cause #3: eval `.generate()` defaulted to max_length=21, truncating predictions against a 256-token target — tanked BLEU/ROUGE independent of model quality. Fixed via `generation_max_length=256`. |
| M2 | 4 | r=8, 3 epochs, pad-masked labels, fp16=False, generation_max_length=256 | BLEU-4 ≥ 0.35 / ROUGE-L ≥ 0.50 | BLEU-4 12.13 (sacrebleu 0-100 scale, ≈0.121 on a 0-1 scale) / ROUGE-L 0.172, training_loss 8.52, eval_loss 1.72 | **First genuinely valid, bug-free attempt.** All three bugs fixed and confirmed active; training_loss real/non-degenerate (not stuck at 0.0), ran a fresh model (not resumed from a stale checkpoint — caught and fixed an accidental silent-resume mid-run, see below). Missed target (~35% of the way there on both metrics), but this is real model/data-quality signal now, not a bug artifact. |

## Definition of done (Phase 4 doc §9)

- [x] M3: `lstm_final.pt` saved — val MAE **not** ≤ 5 (finalized at ~5.7-5.9, documented noise-floor limitation, see experiment_log above)
- [x] M4: best-checkpoint Sentence-Transformers folder saved, Precision@5 = 0.779 ≥ 0.75 logged
- [x] M1: `final/` folder (model + tokenizer) saved — F1 (micro) **not** ≥ 0.85 (finalized at 0.4691, documented heuristic-labels limitation, see experiment_log above)
- [ ] M5: `final/` folder saved, Entity F1 ≥ 0.82 logged on the **gold** test split specifically
- [x] M2: `lora_adapter/` folder saved (adapter only, not merged) — BLEU-4 **not** ≥ 0.35, ROUGE-L **not** ≥ 0.50 (attempt 4: 12.13 / 0.172, first bug-free attempt, see experiment_log above)
- [ ] Every saved artifact lives under `mentora_models/` on Google Drive
