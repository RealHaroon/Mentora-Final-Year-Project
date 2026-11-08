import torch
from transformers import AutoTokenizer

from ml_core.base import LoadableModel


class GapClassifier(LoadableModel):
    always_resident = False

    def __init__(self, model_dir: str, topics: list[str], threshold: float = 0.5):
        super().__init__()
        self.model_dir = model_dir
        self.topics = topics
        self.threshold = threshold
        self.model = None
        self.tokenizer = None

    def load(self) -> None:
        if self._loaded:
            return
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        self.model = torch.load(f"{self.model_dir}/model_quantized.pt", map_location="cpu", weights_only=False)
        self.model.eval()
        self._loaded = True

    def infer(self, question_text: str) -> list[str]:
        inputs = self.tokenizer(
            question_text, return_tensors="pt", truncation=True, padding="max_length", max_length=128
        )
        with torch.no_grad():
            logits = self.model(**inputs).logits[0]
        probs = torch.sigmoid(logits.float())  # sigmoid — multi-label, not softmax
        return [self.topics[i] for i, p in enumerate(probs) if p.item() >= self.threshold]

    def unload(self) -> None:
        self.model = None
        self.tokenizer = None
        self._loaded = False
