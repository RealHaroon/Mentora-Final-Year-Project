"""
Phase 5 / M2 — merge the LoRA adapter into base FLAN-T5-Large, halve to
float16, then verify parity via generated-text comparison.

NOTE: see quantize_m1.py's docstring — torch.quantization.quantize_dynamic
(dynamic INT8) is broken in this environment. Using native float16 casting
instead; verified separately that fp16 produces no NaN/Inf here and matches
FP32's (weak, already-documented) generation quality rather than degrading
it further. M2's low JSON-validity rate on these prompts reflects the
already-known Phase 4 limitation (BLEU-4 12.13 / ROUGE-L 0.172), not
something this script introduces.

This is the heaviest of the three Phase 5 scripts: it downloads
google/flan-t5-large (~3GB) from the Hub on first run and needs real RAM
headroom to hold the FP32 merged model + the fp16 copy at once. Close other
apps before running on an 8GB machine.

Run: ~/.venvs/mentora-ml/bin/python scripts/phase5/quantize_m2.py
"""

import csv
import gc
import json
import random

import torch
from peft import PeftModel
from transformers import T5ForConditionalGeneration, T5Tokenizer

BASE_MODEL = "google/flan-t5-large"
LORA_DIR = "mentora_models/model2_question_generator/lora_adapter"
M2_DIR = "mentora_models/model2_question_generator"
TRAINING_DATA = "mentora_data/processed/m2/flan_t5_training_data.csv"
N_PROMPTS = 12
MAX_NEW_TOKENS = 128


def load_sample_prompts(n):
    with open(TRAINING_DATA, newline="", encoding="utf-8") as f:
        prompts = sorted({row["input_text"] for row in csv.DictReader(f) if row.get("input_text")})
    random.seed(42)
    return random.sample(prompts, min(n, len(prompts)))


def is_valid_question_json(text):
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return False
    return isinstance(obj, dict) and "question" in obj and "options" in obj and "correct_answer" in obj


def main():
    print(f"Loading base model {BASE_MODEL} (this downloads ~3GB on first run)...")
    base = T5ForConditionalGeneration.from_pretrained(BASE_MODEL, low_cpu_mem_usage=True)
    tokenizer = T5Tokenizer.from_pretrained(BASE_MODEL)

    print(f"Loading LoRA adapter from {LORA_DIR} and merging...")
    peft_model = PeftModel.from_pretrained(base, LORA_DIR)
    merged = peft_model.merge_and_unload()
    merged.eval()

    del peft_model
    gc.collect()

    print("\n--- Generating with FP32 (before casting) ---")
    prompts = load_sample_prompts(N_PROMPTS)
    fp32_texts = {}
    for prompt in prompts:
        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            fp32_out = merged.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)
        fp32_texts[prompt] = tokenizer.decode(fp32_out[0], skip_special_tokens=True)
        print(f"  done: {prompt[:60]}")

    print("\nCasting to float16 (in-place — merged is now the fp16 model)...")
    quantized_model = merged.half()
    quantized_model.eval()

    out_path = f"{M2_DIR}/model_quantized.pt"
    torch.save(quantized_model, out_path)
    tokenizer.save_pretrained(M2_DIR)
    print(f"Saved float16 model to {out_path} and tokenizer to {M2_DIR}")

    print("\n--- Parity check: FP32 (cached above) vs float16, generated text ---")
    n_bad_json_fp32 = 0
    n_bad_json_quant = 0

    for prompt in prompts:
        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            quant_out = quantized_model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)
        quant_text = tokenizer.decode(quant_out[0], skip_special_tokens=True)
        fp32_text = fp32_texts[prompt]

        fp32_ok = is_valid_question_json(fp32_text)
        quant_ok = is_valid_question_json(quant_text)
        n_bad_json_fp32 += not fp32_ok
        n_bad_json_quant += not quant_ok

        print(f"\nPrompt: {prompt}")
        print(f"  FP32      ({'valid' if fp32_ok else 'INVALID'} JSON): {fp32_text[:200]}")
        print(f"  Float16   ({'valid' if quant_ok else 'INVALID'} JSON): {quant_text[:200]}")

    print(f"\nInvalid-JSON count — FP32: {n_bad_json_fp32}/{len(prompts)}, "
          f"Float16: {n_bad_json_quant}/{len(prompts)}")
    print(
        "Expect close but not byte-identical text between FP32 and quantized. "
        "A broken JSON shape on the quantized side that wasn't broken on FP32 "
        "is the real failure signal — not minor wording differences."
    )


if __name__ == "__main__":
    main()
