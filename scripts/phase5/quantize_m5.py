"""
Phase 5 / M5 — halve the BERT CV-NER model to float16, then verify parity
against the FP32 original on real resume snippets from the gold set.

NOTE: see quantize_m1.py's docstring — torch.quantization.quantize_dynamic
(dynamic INT8) is broken in this environment (verified: every example here
produced the exact same ~4.14 max-logit-diff regardless of input, a clear
degenerate-output signature, not ordinary INT8 lossiness). Using native
float16 casting instead — verified correct, real 2x size reduction.

Run: ~/.venvs/mentora-ml/bin/python scripts/phase5/quantize_m5.py
"""

import json

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

M5_DIR = "mentora_models/model5_cv_ner/final"
GOLD_SET = "mentora_data/labeled/m5/gold_val_test.jsonl"
N_SAMPLES = 15


def load_sample_token_lists(n):
    examples = []
    with open(GOLD_SET, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            examples.append(json.loads(line)["tokens"])
            if len(examples) >= n:
                break
    return examples


def predicted_tags(model, tokenizer, tokens, id2label):
    enc = tokenizer(tokens, is_split_into_words=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        logits = model(**enc).logits[0]
    pred_ids = logits.argmax(dim=-1).tolist()
    word_ids = enc.word_ids()

    tags = []
    seen = set()
    for pred_id, word_id in zip(pred_ids, word_ids):
        if word_id is None or word_id in seen:
            continue
        seen.add(word_id)
        tags.append(id2label[str(pred_id)])
    return tags


def main():
    tokenizer = AutoTokenizer.from_pretrained(M5_DIR)
    model = AutoModelForTokenClassification.from_pretrained(M5_DIR)
    model.eval()
    id2label = model.config.id2label
    id2label = {str(k): v for k, v in id2label.items()}

    print("Casting to float16...")
    quantized_model = AutoModelForTokenClassification.from_pretrained(M5_DIR, dtype=torch.float16)
    quantized_model.eval()

    out_path = f"{M5_DIR}/model_quantized.pt"
    torch.save(quantized_model, out_path)
    print(f"Saved float16 model to {out_path}")

    print("\n--- Parity check: FP32 vs quantized, per-token predicted tags ---")
    examples = load_sample_token_lists(N_SAMPLES)
    n_mismatch = 0

    for tokens in examples:
        fp32_tags = predicted_tags(model, tokenizer, tokens, id2label)
        quant_tags = predicted_tags(quantized_model, tokenizer, tokens, id2label)

        diff_positions = [i for i, (a, b) in enumerate(zip(fp32_tags, quant_tags)) if a != b]
        preview = " ".join(tokens)[:70]

        if diff_positions:
            n_mismatch += 1
            print(f"[{preview!r}...] {len(diff_positions)} tag(s) differ at positions {diff_positions}")
        else:
            print(f"[{preview!r}...] identical tag sequence")

    print(f"\nExamples with at least one differing tag: {n_mismatch}/{len(examples)}")
    print(
        "Entity boundaries matter more than exact logit values here — a few "
        "isolated tag flips are tolerable, systematic entity-boundary breaks are not."
    )


if __name__ == "__main__":
    main()
