"""
M2 wrapper — FLAN-T5-Large + LoRA (merged, fp16), the heaviest on-demand
model. Already known weak at training time (BLEU-4/ROUGE-L well under
target, see docs/phase10/model_results_table.md); infer() raises
ValueError when its attempt doesn't produce valid JSON, and callers
(routers) catch that and fall back to the real question bank rather than
show a broken page.
"""

import json

import torch
from transformers import AutoTokenizer

from ml_core.base import LoadableModel


class QuestionGenerator(LoadableModel):
    always_resident = False

    def __init__(self, model_dir: str):
        super().__init__()
        self.model_dir = model_dir
        self.model = None
        self.tokenizer = None

    def load(self) -> None:
        if self._loaded:
            return
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        self.model = torch.load(f"{self.model_dir}/model_quantized.pt", map_location="cpu", weights_only=False)
        self.model.eval()
        self._loaded = True

    def infer(self, topic: str, difficulty: str = "medium") -> dict:
        # Match training's exact prompt format (mentora_data/processed/m2/
        # flan_t5_training_data.csv's input_text) — no extra instruction text.
        # Phase 5's parity check already showed this model is weak (12/12
        # invalid JSON even on FP32, a known limitation, not a quantization
        # bug — see scripts/phase5/README.md); an out-of-distribution prompt
        # would only make that worse.
        prompt = f"Generate a {difficulty} difficulty multiple-choice question about {topic}."
        inputs = self.tokenizer(prompt, return_tensors="pt")

        # Used to retry up to 2 more times with sampling on a failed attempt.
        # Removed 2026-11-13 after confirming empirically — across the 12
        # prompts in the Phase 5 parity check plus a direct test against all
        # 20 real question-bank topics, 32/32 — that a retry never turns a
        # failed generation into valid JSON here; it only tripled the latency
        # (~35-45s) of a call that was always going to fall back anyway.
        with torch.no_grad():
            output_ids = self.model.generate(**inputs, max_new_tokens=200)
        text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        parsed = self._try_parse(text)
        if parsed is not None:
            return parsed
        # Failed to produce valid JSON — surface this rather than silently
        # returning malformed data to the frontend.
        raise ValueError("Question generator failed to produce valid JSON")

    @staticmethod
    def _try_parse(text: str) -> dict | None:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        # "correct_answer" key presence is checked, not its value — training
        # data itself often has correct_answer=null and fewer than 4 options,
        # so requiring a full A-D set would reject the model's own ground truth.
        if not ({"question", "options", "correct_answer"} <= parsed.keys()):
            return None
        if not isinstance(parsed["options"], dict) or not parsed["options"]:
            return None
        return parsed

    def unload(self) -> None:
        self.model = None
        self.tokenizer = None
        self._loaded = False
