import numpy as np
from sentence_transformers import SentenceTransformer

from ml_core.base import LoadableModel


class CareerMatcher(LoadableModel):
    always_resident = True

    def __init__(self, model_path: str, career_catalogue: list[dict]):
        super().__init__()
        self.model_path = model_path
        self.career_catalogue = career_catalogue  # [{"career_id": ..., "title": ..., "text": "<skills description>"}]
        self.model: SentenceTransformer | None = None
        self.career_embeddings: np.ndarray | None = None

    def load(self) -> None:
        if self._loaded:
            return
        self.model = SentenceTransformer(self.model_path)
        # Precompute career embeddings ONCE at load time, not per request —
        # the catalogue doesn't change between requests.
        self.career_embeddings = self.model.encode(
            [c["text"] for c in self.career_catalogue], convert_to_numpy=True
        )
        self._loaded = True

    def infer(self, skill_text: str, top_k: int = 5) -> list[dict]:
        skill_emb = self.model.encode(skill_text, convert_to_numpy=True)
        sims = self.career_embeddings @ skill_emb / (
            np.linalg.norm(self.career_embeddings, axis=1) * np.linalg.norm(skill_emb) + 1e-9
        )
        top_idx = np.argsort(-sims)[:top_k]
        return [
            {
                "career_id": self.career_catalogue[i]["career_id"],
                "career_title": self.career_catalogue[i]["title"],
                "match_score": round(float(sims[i]) * 100),
            }
            for i in top_idx
        ]

    def unload(self) -> None:
        pass  # never called — always_resident
