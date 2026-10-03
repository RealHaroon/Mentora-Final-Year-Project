# Phase 4 — experiment log

Fill in one row per training attempt. Reusable directly in the thesis's
"model training results — targets vs. achieved" chapter
(`docs/phases/MENTORA_Phase4_Model_Training.md` §7).

| Model | Attempt | Key hyperparams changed | Target metric | Achieved | Notes |
|---|---|---|---|---|---|
| M3 | 1 | hidden_size=128, 30 epochs | MAE ≤ 5 | — | — |
| M4 | 1 | 4 epochs, r=8 | P@5 ≥ 0.75 | — | — |
| M1 | 1 | lr=2e-5, 5 epochs | F1 ≥ 0.85 | — | — |
| M5 | 1 | 4 epochs | Entity F1 ≥ 0.82 | — | — |
| M2 | 1 | r=8, 3 epochs | BLEU-4 ≥ 0.35 / ROUGE-L ≥ 0.50 | — | — |

## Definition of done (Phase 4 doc §9)

- [ ] M3: `lstm_final.pt` saved, val MAE ≤ 5 logged
- [ ] M4: best-checkpoint Sentence-Transformers folder saved, Precision@5 ≥ 0.75 logged
- [ ] M1: `final/` folder (model + tokenizer) saved, F1 (micro) ≥ 0.85 logged on held-out test
- [ ] M5: `final/` folder saved, Entity F1 ≥ 0.82 logged on the **gold** test split specifically
- [ ] M2: `lora_adapter/` folder saved (adapter only, not merged), BLEU-4 ≥ 0.35 and ROUGE-L ≥ 0.50 logged
- [ ] Every saved artifact lives under `mentora_models/` on Google Drive
