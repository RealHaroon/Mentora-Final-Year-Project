"""
Phase 5 / M1 — halve the DeBERTa gap classifier to float16, then verify
parity against the FP32 original before trusting the result.

NOTE: the Phase 5 doc originally called for torch.quantization.quantize_dynamic
(dynamic INT8). Verified empirically that this is broken in this environment
(torch 2.15 + Python 3.14) — it produces near-constant, degenerate logits
regardless of input (max abs diff ~5 on a model whose fp32 logits span about
-3 to +3), not the "handful of borderline flips" the doc expects. The legacy
torch.ao.quantization path is itself flagged deprecated/slated for removal in
the warnings it prints, consistent with this being a backend bug rather than
expected INT8 lossiness. Switched to native float16 casting instead: verified
near-zero diff (~0.001-0.002) and a real, confirmed 2x size reduction
(737MB -> 369MB), at half the compression of the originally planned INT8 but
actually trustworthy.

Run: ~/.venvs/mentora-ml/bin/python scripts/phase5/quantize_m1.py
"""

import json
import random

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

M1_DIR = "mentora_models/model1_gap_classifier/final"
QUESTION_BANK = "mentora_data/processed/m1/question_bank_final.csv"
THRESHOLD = 0.5
N_SAMPLES = 20


def load_sample_questions(n):
    import csv

    with open(QUESTION_BANK, newline="", encoding="utf-8") as f:
        rows = [r["question_text"] for r in csv.DictReader(f) if r.get("question_text")]
    random.seed(42)
    return random.sample(rows, min(n, len(rows)))


def predicted_labels(logits, topic_labels):
    probs = 1 / (1 + np.exp(-logits))
    preds = probs >= THRESHOLD
    return {topic_labels[i] for i, flag in enumerate(preds) if flag}


def main():
    with open(f"{M1_DIR}/topic_labels.json") as f:
        topic_labels = json.load(f)

    tokenizer = AutoTokenizer.from_pretrained(M1_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(M1_DIR)
    model.eval()

    print("Casting to float16...")
    quantized_model = AutoModelForSequenceClassification.from_pretrained(M1_DIR, dtype=torch.float16)
    quantized_model.eval()

    out_path = f"{M1_DIR}/model_quantized.pt"
    torch.save(quantized_model, out_path)
    print(f"Saved float16 model to {out_path}")

    print("\n--- Parity check: FP32 vs float16, predicted label sets ---")
    questions = load_sample_questions(N_SAMPLES)
    n_mismatch = 0
    max_abs_diff = 0.0

    for text in questions:
        inputs = tokenizer(text, truncation=True, return_tensors="pt")
        with torch.no_grad():
            fp32_logits = model(**inputs).logits[0].numpy()
            quant_logits = quantized_model(**inputs).logits[0].float().numpy()

        max_abs_diff = max(max_abs_diff, float(np.abs(fp32_logits - quant_logits).max()))

        fp32_set = predicted_labels(fp32_logits, topic_labels)
        quant_set = predicted_labels(quant_logits, topic_labels)

        flag = ""
        if fp32_set != quant_set:
            n_mismatch += 1
            flag = "  <-- MISMATCH"

        print(f"[{text[:60]!r}] fp32={sorted(fp32_set)} quant={sorted(quant_set)}{flag}")

    print(f"\nMax abs logit diff across {len(questions)} examples: {max_abs_diff:.4f}")
    print(f"Label-set mismatches: {n_mismatch}/{len(questions)}")
    print(
        "A handful of mismatches near the 0.5 threshold is expected and fine; "
        "widespread mismatches mean the quantized file should not be trusted."
    )


if __name__ == "__main__":
    main()
