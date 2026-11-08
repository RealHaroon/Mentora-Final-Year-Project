"""
Phase 5 §6 + §7 — local smoke test and size/latency benchmark.

Run ON THE LAPTOP (not Colab): loads each model fresh from disk (the real
deployment path, not the in-memory object from the quantize_*.py scripts)
and times one cold load + one inference per model. Catches a torch-version
mismatch between the Colab training environment and this local install,
independent of the fp16 switch covered in quantize_m1/m2/m5.py.

Run: ~/.venvs/mentora-ml/bin/python scripts/phase5/benchmark_and_smoke_test.py
"""

import os
import time

import torch
import torch.nn as nn
from transformers import AutoTokenizer

M1_DIR = "mentora_models/model1_gap_classifier/final"
M2_DIR = "mentora_models/model2_question_generator"
M3_PATH = "mentora_models/model3_trajectory_predictor/lstm_final.pt"
M4_DIR = "mentora_models/model4_career_matcher"
M5_DIR = "mentora_models/model5_cv_ner/final"

results = []


def dir_size_mb(path):
    if os.path.isfile(path):
        return os.path.getsize(path) / 1e6
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total / 1e6


def record(name, fp32_mb, quant_mb, load_s, infer_s, note=""):
    results.append((name, fp32_mb, quant_mb, load_s, infer_s, note))
    print(f"{name}: load {load_s:.2f}s, inference {infer_s:.3f}s, "
          f"size {quant_mb:.0f}MB (fp32 was {fp32_mb:.0f}MB){' -- ' + note if note else ''}")


class TrajectoryLSTM(nn.Module):
    def __init__(self, input_size=1, hidden_size=128, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :]).squeeze(-1)


def test_m1():
    t0 = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(M1_DIR)
    model = torch.load(f"{M1_DIR}/model_quantized.pt", map_location="cpu", weights_only=False)
    model.eval()
    load_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    inputs = tokenizer("A quadratic equation has the form ax squared plus bx plus c equals zero.",
                        return_tensors="pt")
    with torch.no_grad():
        out = model(**inputs)
    infer_s = time.perf_counter() - t0
    assert out.logits.shape[-1] == 20, f"unexpected logits shape {out.logits.shape}"

    fp32_mb = dir_size_mb(f"{M1_DIR}/model.safetensors")
    record("M1", fp32_mb, dir_size_mb(f"{M1_DIR}/model_quantized.pt"), load_s, infer_s)


def test_m2():
    t0 = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(M2_DIR)
    model = torch.load(f"{M2_DIR}/model_quantized.pt", map_location="cpu", weights_only=False)
    model.eval()
    load_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    inputs = tokenizer("Generate a medium difficulty multiple-choice question about Algebra.",
                        return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=32)
    infer_s = time.perf_counter() - t0
    text = tokenizer.decode(out[0], skip_special_tokens=True)
    assert len(text) > 0, "empty generation"

    record("M2", 2950, dir_size_mb(f"{M2_DIR}/model_quantized.pt"), load_s, infer_s)


def test_m3():
    t0 = time.perf_counter()
    model = TrajectoryLSTM()
    state_dict = torch.load(M3_PATH, map_location="cpu", weights_only=False)
    model.load_state_dict(state_dict)
    model.eval()
    load_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    dummy_seq = torch.rand(1, 5, 1)  # SEQ_LEN=5, 1 feature, matches training config
    with torch.no_grad():
        out = model(dummy_seq)
    infer_s = time.perf_counter() - t0
    assert out.shape == (1,), f"unexpected output shape {out.shape}"

    record("M3", dir_size_mb(M3_PATH), dir_size_mb(M3_PATH), load_s, infer_s, note="no quantization needed")


def test_m4():
    from sentence_transformers import SentenceTransformer

    t0 = time.perf_counter()
    model = SentenceTransformer(M4_DIR)
    load_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    emb = model.encode(["Software engineer with 3 years of Python and ML experience."])
    infer_s = time.perf_counter() - t0
    assert emb.shape[-1] > 0

    record("M4", dir_size_mb(M4_DIR), dir_size_mb(M4_DIR), load_s, infer_s, note="no quantization needed")


def test_m5():
    from transformers import AutoTokenizer as AT

    t0 = time.perf_counter()
    tokenizer = AT.from_pretrained(M5_DIR)
    model = torch.load(f"{M5_DIR}/model_quantized.pt", map_location="cpu", weights_only=False)
    model.eval()
    load_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    inputs = tokenizer(["Python", "developer", "with", "AWS", "experience"],
                        is_split_into_words=True, return_tensors="pt")
    with torch.no_grad():
        out = model(**inputs)
    infer_s = time.perf_counter() - t0
    assert out.logits.shape[-1] == 7, f"unexpected logits shape {out.logits.shape}"

    fp32_mb = dir_size_mb(f"{M5_DIR}/model.safetensors")
    record("M5", fp32_mb, dir_size_mb(f"{M5_DIR}/model_quantized.pt"), load_s, infer_s)


def main():
    print("--- Phase 5 §6 local smoke test + §7 benchmark (fresh load from disk) ---\n")
    for name, fn in [("M1", test_m1), ("M2", test_m2), ("M3", test_m3), ("M4", test_m4), ("M5", test_m5)]:
        try:
            fn()
        except Exception as e:
            print(f"{name}: FAILED -- {type(e).__name__}: {e}")
            results.append((name, None, None, None, None, f"FAILED: {e}"))

    print("\n--- Summary table (for Phase 5 doc §7) ---")
    print(f"{'Model':<6}{'FP32 (MB)':>12}{'On-disk (MB)':>14}{'Load (s)':>10}{'Inference (s)':>16}")
    for name, fp32_mb, quant_mb, load_s, infer_s, note in results:
        if load_s is None:
            print(f"{name:<6}{'--':>12}{'--':>14}{'--':>10}{'--':>16}  {note}")
        else:
            print(f"{name:<6}{fp32_mb:>12.0f}{quant_mb:>14.0f}{load_s:>10.2f}{infer_s:>16.3f}  {note}")


if __name__ == "__main__":
    main()
