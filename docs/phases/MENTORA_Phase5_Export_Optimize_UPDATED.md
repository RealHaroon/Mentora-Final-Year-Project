# MENTORA — Phase 5 Deep Dive: Export & Optimize for Local Inference
### *(Updated — AVX2 confirmed present on the target laptop; ONNX Runtime detour removed)*

*Prerequisite: Phase 4 is done — all five trained models sit in
`mentora_models/model{1..5}_*/` on Google Drive, each meeting its target metric. This
phase converts them into a form that will actually run on your 8GB laptop, downloads
them locally, and proves they load and run there before Phase 6 wires them into the
backend. Estimated time: 1–3 days — shorter than originally planned, since there's no
ONNX export step to debug. Plus however long the Drive downloads take.*

---

## 0. Recap — what needs converting, and why

| Model | Needs quantization? | Why |
|---|---|---|
| M3 (LSTM) | **No** | ~2MB, plain FP32 is already cheap enough to run always-resident |
| M4 (Sentence-Transformers) | **No** | ~420MB FP32 is acceptable always-resident; quantizing buys little and Sentence-Transformers' own PyTorch path is simplest to keep |
| M1 (DeBERTa Gap Classifier) | **Yes** | Full FP32 DeBERTa-base is the heaviest of the on-demand models; INT8 shrinks both RAM and load time meaningfully |
| M5 (BERT NER) | **Yes** | Same reasoning as M1 |
| M2 (FLAN-T5-Large + LoRA) | **Yes** | The single largest model in the project — quantization matters most here |

**Why plain PyTorch quantization, and not ONNX Runtime:** the original plan assumed a
3rd-Gen i5 with no AVX2, which would crash PyTorch's default `FBGEMM` quantization
backend. `cat /proc/cpuinfo | grep flags | grep -o avx2` confirmed AVX2 **is** present
on this laptop, so that failure mode doesn't apply here — `torch.quantization.
quantize_dynamic()` works directly, with no export step, no extra dependency
(`optimum-onnx`/`onnxruntime`), and no separate graph format to keep in sync with the
original model.

---

## 1. M3 and M4 — no conversion needed, just package for download

### 1.1 M3
Already saved as `lstm_final.pt` in Phase 4. Nothing to do here except confirm it's
there and small:
```python
import os
path = '/content/drive/MyDrive/mentora_models/model3_trajectory_predictor/lstm_final.pt'
print(os.path.getsize(path) / 1e6, "MB")  # expect ~1-3MB
```

### 1.2 M4
Already saved as a full Sentence-Transformers folder by `model.fit(..., save_best_model=True)`
in Phase 4. Confirm the folder has the expected files (`config.json`,
`model.safetensors` or `pytorch_model.bin`, `tokenizer.json`, etc.) and note its size
(~420MB) — this is the largest thing that stays as plain PyTorch, and it's why the
master plan keeps it always-resident rather than lazy-loaded (loading it fresh on
every request would be slower than just keeping it in RAM).

**That's the entirety of this step for M3/M4** — both get downloaded as-is in §5.

---

## 2. M1 — DeBERTa Gap Classifier: quantize

```python
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

M1_DIR = '/content/drive/MyDrive/mentora_models/model1_gap_classifier/final'

model = AutoModelForSequenceClassification.from_pretrained(M1_DIR)
model.eval()

quantized_model = torch.quantization.quantize_dynamic(
    model, {torch.nn.Linear}, dtype=torch.qint8
)

# Save the full quantized module (not a state_dict) — quantized layers change the
# module structure, so a state_dict alone can't be reloaded into a fresh model.
torch.save(quantized_model, f'{M1_DIR}/model_quantized.pt')

tokenizer = AutoTokenizer.from_pretrained(M1_DIR)
tokenizer.save_pretrained(f'{M1_DIR}')  # tokenizer files travel alongside the .pt
```

### 2.1 Verify parity — original vs. quantized, on the SAME input
Never skip this step. A quantized model that silently produces different predictions
than the original is worse than no quantization at all.
```python
import torch, numpy as np

text = "A quadratic equation has the form ax² + bx + c = 0."
inputs = tokenizer(text, return_tensors="pt")

with torch.no_grad():
    fp32_logits = model(**inputs).logits
    quant_logits = quantized_model(**inputs).logits

print("Max abs diff:", (fp32_logits - quant_logits).abs().max().item())
# INT8 is lossy by design — a diff under ~0.1-0.3 on typical logit scales is normal.
# The real check is whether predicted LABELS flip on a batch of known examples,
# not raw logit distance.
```
Run this on a batch of 15–20 known validation examples, not just one string, and
specifically check that the **predicted multi-label set** (after the sigmoid +
threshold from Phase 4 §4.2) matches between FP32 and quantized for most of them — a
handful of borderline flips near the 0.5 threshold is expected and fine; a lot of them
is a sign to re-check the quantization config.

---

## 3. M5 — BERT NER: quantize

Identical pattern to M1, using the token-classification class:
```python
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

M5_DIR = '/content/drive/MyDrive/mentora_models/model5_cv_ner/final'

model = AutoModelForTokenClassification.from_pretrained(M5_DIR)
model.eval()

quantized_model = torch.quantization.quantize_dynamic(
    model, {torch.nn.Linear}, dtype=torch.qint8
)
torch.save(quantized_model, f'{M5_DIR}/model_quantized.pt')

tokenizer = AutoTokenizer.from_pretrained(M5_DIR)
tokenizer.save_pretrained(M5_DIR)
```
For parity-checking a token-classification model, compare the **per-token predicted
tag sequence** (after `argmax`, mapped through `id2tag`) between FP32 and quantized on
a handful of real resume snippets from the Phase 3 gold set — entity boundaries
matter more than exact logit values here.

---

## 4. M2 — FLAN-T5-Large + LoRA: merge, then quantize

### 4.1 Step 1 — merge the LoRA adapter into the base model first
This step is unchanged regardless of quantization approach — it's about
consolidating the fine-tune into one deployable model, not about AVX2:
```python
from peft import PeftModel
from transformers import T5ForConditionalGeneration, T5Tokenizer

base = T5ForConditionalGeneration.from_pretrained('google/flan-t5-large')
peft_model = PeftModel.from_pretrained(base, '/content/drive/MyDrive/mentora_models/model2_question_generator/lora_adapter')
merged = peft_model.merge_and_unload()   # bakes the LoRA delta into the base weights

M2_DIR = '/content/drive/MyDrive/mentora_models/model2_question_generator'
tokenizer = T5Tokenizer.from_pretrained('google/flan-t5-large')
merged.eval()
```

### 4.2 Step 2 — quantize the merged model
```python
import torch

quantized_model = torch.quantization.quantize_dynamic(
    merged, {torch.nn.Linear}, dtype=torch.qint8
)
torch.save(quantized_model, f'{M2_DIR}/model_quantized.pt')
tokenizer.save_pretrained(M2_DIR)
```
No intermediate ~3GB merged FP32 folder needs to be kept around this time — only the
quantized `.pt` needs to reach the laptop.

### 4.3 Verify parity — compare GENERATED TEXT, not raw logits
For a generation model, the meaningful check is end-to-end output text:
```python
prompt = "Generate a medium difficulty multiple-choice question about Algebra (Quadratic Equations)."
inputs = tokenizer(prompt, return_tensors="pt")

with torch.no_grad():
    pt_out = merged.generate(**inputs, max_new_tokens=128)
    quant_out = quantized_model.generate(**inputs, max_new_tokens=128)

print("Original:", tokenizer.decode(pt_out[0], skip_special_tokens=True))
print("Quantized:", tokenizer.decode(quant_out[0], skip_special_tokens=True))
```
Run this across 10–15 varied prompts (different topics/difficulties). Expect close
but not always byte-identical output — check that the JSON structure from Phase 3's
`target_text` format (question/options/correct_answer keys) still comes out valid and
parseable (`json.loads(...)`) on every prompt; a few word choices differing is fine, a
broken JSON shape is not.

---

## 5. Downloading everything from Drive to the local laptop

### 5.1 What to actually download
- `model1_gap_classifier/model_quantized.pt` + tokenizer files
- `model2_question_generator/model_quantized.pt` + tokenizer files
- `model3_trajectory_predictor/lstm_final.pt`
- `model4_career_matcher/` (the full Sentence-Transformers folder, as-is)
- `model5_cv_ner/model_quantized.pt` + tokenizer files

One `.pt` file per model now instead of a `*_quantized.onnx` plus tokenizer folder —
and for M2, one file instead of three separate graph files.

### 5.2 Zip each model folder in Colab, download the zips
```python
import shutil
for name in ['model1_gap_classifier', 'model2_question_generator',
             'model3_trajectory_predictor', 'model4_career_matcher', 'model5_cv_ner']:
    src = f'/content/drive/MyDrive/mentora_models/{name}'
    shutil.make_archive(f'/content/{name}', 'zip', src)
```
Then use Colab's file browser (left sidebar → folder icon) to right-click each `.zip`
in `/content/` and Download — or, simpler for larger files, install the Google Drive
desktop app on the laptop and let it sync `mentora_models/` directly.

### 5.3 Place them into the backend's expected folder structure
Per the master plan's §9 folder layout:
```
mentora/ml_models/saved/
├── model1_gap_classifier/        # model_quantized.pt + tokenizer files
├── model2_question_generator/    # model_quantized.pt + tokenizer files
├── model3_trajectory_predictor/  # lstm_final.pt
├── model4_career_matcher/        # the full Sentence-Transformers folder
└── model5_cv_ner/                # model_quantized.pt + tokenizer files
```

---

## 6. Local smoke test

Before Phase 6 wires any of this into FastAPI, run one small local script per
quantized model to confirm it loads and runs on this specific machine — this also
catches a torch-version mismatch between the Colab training environment and the local
install, which is a real risk independent of AVX2.

```python
# local_smoke_test.py — run this ON THE LAPTOP, not in Colab
import torch
from transformers import AutoTokenizer

MODEL_DIR = "ml_models/saved/model1_gap_classifier"
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = torch.load(f"{MODEL_DIR}/model_quantized.pt", map_location="cpu", weights_only=False)
model.eval()

inputs = tokenizer("A quadratic equation has the form ax squared plus bx plus c equals zero.",
                    return_tensors="pt")
with torch.no_grad():
    outputs = model(**inputs)
print("Inference succeeded. Logits shape:", outputs.logits.shape)
```
Run the equivalent for M5 and M2. `weights_only=False` is required since this loads a
full pickled module, not just tensor weights — safe here since you produced the file
yourself in a notebook you control.

---

## 7. Size and latency benchmark (fill this in on the real laptop — numbers vary by machine)

| Model | FP32 size | Quantized size | Load time (cold) | One inference (CPU) |
|---|---|---|---|---|
| M1 | ~370MB | ~ (fill in) | — | — |
| M2 | ~3GB | ~ (fill in) | — | — |
| M3 | ~2MB (no quant) | n/a | — | — |
| M4 | ~420MB (no quant) | n/a | — | — |
| M5 | ~420MB | ~ (fill in) | — | — |

Time each with a simple `time.perf_counter()` wrapper around the load call and one
forward pass, on the actual laptop, not Colab — Colab's CPU is a different (and much
faster) chip than the one this app has to run on.

---

## 8. Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Quantized model's predictions look totally different, not just slightly off | Quantized an already-quantized object, or loaded the wrong file | Re-run from a clean `quantize_dynamic()` call each time; always diff against the *original* FP32 model, not a previous quantized attempt |
| M2 quantization fails partway with a shape/dtype error | Tried quantizing the `PeftModel` directly instead of the merged model | Always call `merge_and_unload()` first (§4.1) — quantization doesn't understand LoRA's adapter layers |
| `torch.load(...)` fails locally with a pickle/version error | PyTorch version mismatch between Colab (training) and the local install | Match the local `pip install torch` version to what Colab used, or re-save with `torch.save(quantized_model.state_dict(), ...)` and reconstruct the architecture locally instead of pickling the full object |
| Drive download is extremely slow / keeps failing | Trying to download several GB over a slow connection in one browser download | Use the Google Drive desktop sync client instead of manual zip-and-download (§5.2) — it resumes automatically on interruption |
| M2's generated JSON is malformed after quantization on some prompts | INT8 quantization degraded output quality more than expected for this specific model | Try quantizing only a subset of layers, or fall back to FP32 for M2 specifically if generation quality visibly suffers — a legitimate compromise given M2 is the least RAM-constrained of the three on-demand models now that ONNX's smaller footprint isn't part of the equation |

---

## 9. Definition of done

- [x] M1: `model_quantized.pt` + tokenizer files in `ml_models/saved/model1_gap_classifier/`,
      parity-checked against FP32 on 20 examples — 0/20 label-set mismatches.
      **Not INT8** — `torch.quantization.quantize_dynamic` is broken in this
      environment (produces degenerate output); switched to float16 casting.
      See `scripts/phase5/README.md`.
- [x] M5: same, in `model5_cv_ner/`, parity-checked on 15 real resume snippets —
      3/15 with one isolated tag flip (within this section's own tolerance).
      Same INT8→fp16 switch as M1.
- [x] M2: LoRA adapter merged, quantized (fp16, same reason as above), in
      `model2_question_generator/`, parity-checked via generated-text comparison
      on 12 prompts — **valid-JSON output NOT confirmed: 12/12 invalid on both
      FP32 and fp16.** This is an inherited Phase 4 limitation (BLEU-4 12.13 /
      ROUGE-L 0.172), not a quantization defect — fp16 reproduces FP32's failure
      rate exactly, no new divergence. Documented, not pursued further per the
      earlier "stop here, move to Phase 5" decision. See `scripts/phase5/README.md`.
- [x] M3: `lstm_final.pt` in `model3_trajectory_predictor/`
- [x] M4: full Sentence-Transformers folder in `model4_career_matcher/`
- [x] §6's local smoke test passes for every quantized model, **on the actual target
      laptop** — all 5 models (M1-M5) load fresh from disk and run one inference
      with no pickle/version errors. See `scripts/phase5/benchmark_and_smoke_test.py`.
- [x] §7's benchmark table filled in with real local numbers:

  | Model | FP32 size | On-disk size | Load time | Inference time |
  |---|---|---|---|---|
  | M1 | 738MB | 369MB | 3.86s | 0.663s |
  | M2 | 2950MB | 1567MB | 4.62s | 3.70s (32-token generate) |
  | M3 | 1MB | 1MB | 0.01s | 0.057s |
  | M4 | 439MB | 439MB | 1.04s | 0.544s |
  | M5 | 436MB | 218MB | 0.73s | 0.044s |

Once every row is checked, Phase 6 (Model Manager + real inference wiring) can begin
— it consumes exactly this `ml_models/saved/` folder structure, swapping Phase 2's
mock JSON responses for real calls into these files one endpoint at a time.
