import re

import torch
from transformers import AutoTokenizer

from ml_core.base import LoadableModel

# Training data's "tokens" column was produced by spaCy, which splits
# punctuation off words (see datasets/m5_cv_ner/build_ner_dataset.py) — e.g.
# "Python," is two tokens, "Python" and ",". A plain str.split() leaves
# punctuation stuck to words and measurably hurts entity boundaries.
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


class CVNerExtractor(LoadableModel):
    always_resident = False

    def __init__(self, model_dir: str, id2tag: dict[int, str]):
        super().__init__()
        self.model_dir = model_dir
        self.id2tag = id2tag
        self.model = None
        self.tokenizer = None

    def load(self) -> None:
        if self._loaded:
            return
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        self.model = torch.load(f"{self.model_dir}/model_quantized.pt", map_location="cpu", weights_only=False)
        self.model.eval()
        self._loaded = True

    def infer(self, cv_text: str) -> dict:
        # Long CVs may exceed the model's max length — chunk on paragraph breaks.
        chunks = self._chunk(cv_text, max_chars=800)
        # Entity types come from the trained tag set itself (id2tag), not a
        # hardcoded guess — this model's actual labels are CERT/DEGREE/GPA/SKILL,
        # no PROJECT tag exists, so don't assume one.
        entities: dict[str, set] = {}

        for chunk in chunks[:6]:  # cap total chunks per upload — see Phase 6 doc's pitfalls table
            tokens = _TOKEN_RE.findall(chunk)
            if not tokens:
                continue
            enc = self.tokenizer(
                tokens, is_split_into_words=True, return_tensors="pt",
                truncation=True, padding="max_length", max_length=256,
            )
            with torch.no_grad():
                logits = self.model(**enc).logits[0]
            preds = torch.argmax(logits, dim=-1)
            self._decode_bio(tokens, preds, enc, entities)

        return {
            "skills": sorted(entities.get("SKILL", set())),
            "certifications": sorted(entities.get("CERT", set())),
            "degrees": sorted(entities.get("DEGREE", set())),
            "gpa": next(iter(entities.get("GPA", set())), None),
        }

    def _chunk(self, text: str, max_chars: int) -> list[str]:
        paras = text.split("\n\n")
        chunks, current = [], ""
        for p in paras:
            if len(current) + len(p) > max_chars:
                if current:
                    chunks.append(current)
                current = p
            else:
                current += "\n\n" + p
        if current:
            chunks.append(current)
        return chunks or [text[:max_chars]]

    def _decode_bio(self, tokens, preds, enc, entities: dict[str, set]):
        # word_ids repeats the same index across a word's wordpiece subtokens
        # (e.g. "TensorFlow" -> ["Tensor", "##Flow"], both word_id=6). A
        # model that tags B- then I- across those subtokens (a real, imperfect
        # but valid BIO sequence) must not append the resolved whole word
        # twice — track the last word_id actually appended per entity.
        word_ids = enc.word_ids(batch_index=0)
        current_entity: list[str] = []
        current_type: str | None = None
        last_word_id: int | None = None
        for i, pred_id in enumerate(preds.tolist()):
            tag = self.id2tag[int(pred_id)]
            word_id = word_ids[i]
            if tag.startswith("B-"):
                if current_entity and current_type:
                    entities.setdefault(current_type, set()).add(" ".join(current_entity))
                current_type = tag[2:]
                current_entity = [tokens[word_id]] if word_id is not None else []
                last_word_id = word_id
            elif tag.startswith("I-") and current_type == tag[2:] and word_id is not None:
                if word_id != last_word_id:
                    current_entity.append(tokens[word_id])
                    last_word_id = word_id
            else:
                if current_entity and current_type:
                    entities.setdefault(current_type, set()).add(" ".join(current_entity))
                current_entity, current_type, last_word_id = [], None, None
        if current_entity and current_type:
            entities.setdefault(current_type, set()).add(" ".join(current_entity))

    def unload(self) -> None:
        self.model = None
        self.tokenizer = None
        self._loaded = False
