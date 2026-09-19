"""
M5 dataset — CV/Transcript NER Extractor.

Source: Kaggle "Updated Resume Dataset" (jillanisofttech/updated-resume-dataset,
CC0), 962 raw resume texts across 25 job categories.

Semi-automated BIO-tagging bootstrap, per docs/phases/MENTORA_Phase3_Datasets.md
§5.3:
  1. Auto-tag SKILL spans via spaCy PhraseMatcher against the technical skill
     vocabulary already extracted from M4's job postings (§ build_training_pairs.py)
     — much better fit for resume text than O*NET's generic skill names.
  2. Auto-tag CERT spans against a fixed vocabulary of common certifications.
  3. Auto-tag GPA and DEGREE via regex (both are pattern-friendly, no
     vocabulary list needed).
  4. Split into a "gold" sample that a human MUST hand-correct before it's
     trustworthy (this script only auto-tags — it does not replace manual
     review) and a larger "silver" (auto-tagged, uncorrected) set used only
     for training, per the doc's standard gold/silver trade-off.

Run: ~/.venvs/mentora-data/bin/python datasets/m5_cv_ner/build_ner_dataset.py
Output:
  mentora_data/labeled/m5/gold_val_test.jsonl   (NEEDS MANUAL REVIEW — see below)
  mentora_data/labeled/m5/silver_train.jsonl    (auto-tagged, used as-is)
  mentora_data/labeled/m5/gold_review.csv       (human-readable version of the
                                                   gold set, one row per resume,
                                                   for the actual hand-correction
                                                   pass — see docs/phases/
                                                   MENTORA_Phase3_Datasets.md §5.3
                                                   step 3 for the doccano option)
"""

import json
import re
from pathlib import Path

import pandas as pd
import spacy
from spacy.matcher import PhraseMatcher

RAW_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "raw"
OUT_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "labeled" / "m5"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GOLD_SAMPLE_SIZE = 150
SEED = 13

CERT_VOCAB = [
    "AWS Certified", "AWS Certified Solutions Architect", "AWS Certified Developer",
    "PMP", "PMI-ACP", "CFA", "CPA", "Google Analytics", "Google Ads",
    "Scrum Master", "Certified Scrum Master", "CSM", "Six Sigma",
    "Microsoft Certified", "Azure Certified", "CCNA", "CCNP", "CompTIA",
    "CompTIA Security+", "CEH", "CISSP", "CISA", "Salesforce Certified",
    "Oracle Certified", "Red Hat Certified", "ITIL", "Tableau Certified",
]

DEGREE_VOCAB = [
    "BS", "B.S.", "BSc", "B.Sc", "BE", "B.E.", "BTech", "B.Tech",
    "MS", "M.S.", "MSc", "M.Sc", "ME", "M.E.", "MTech", "M.Tech",
    "MBA", "PhD", "Ph.D.", "Bachelor", "Bachelors", "Master", "Masters",
    "Doctorate", "Associate Degree",
]

# This dataset (Indian/South-Asian tech resumes) reports academic scores as
# CGPA out of 10 far more often than GPA out of 4.0 — checked empirically
# (22 "/10" matches vs. 4 "/4.0" matches across the corpus). Cover both.
GPA_PATTERN = re.compile(r"\b\d{1,2}\.\d{1,2}\s*/\s*(?:4\.0|10)\b")

# Fixed-vocabulary CERT matching (PhraseMatcher, exact phrases) misses most
# real mentions here — certs are phrased freely ("Microsoft Certified Systems
# Engineer", "Java Developer Certificate", "PRINCE2 practitioner") rather than
# from a short fixed list. A regex catches the two dominant phrasings
# generically; CERT_VOCAB below still catches acronym-style certs regex won't.
CERT_REGEX = re.compile(
    r"\b(?:[A-Z][\w&]*\s+){0,3}Certified(?:\s+[A-Z][\w&]*){0,4}"
    r"|\b[A-Z][\w&]*(?:\s+[A-Z][\w&]*){0,3}\s+Certificate\b"
)


def load_skill_vocab() -> list[str]:
    jobs = pd.read_csv(RAW_DIR / "kaggle_job_postings" / "job_dataset.csv")
    vocab = set()
    for s in jobs["Skills"].dropna():
        for part in s.split(";"):
            part = part.strip()
            if part and len(part) < 40:
                vocab.add(part)
    return sorted(vocab)


def build_matcher(nlp) -> PhraseMatcher:
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher.add("SKILL", [nlp.make_doc(s) for s in load_skill_vocab()])
    matcher.add("CERT", [nlp.make_doc(c) for c in CERT_VOCAB])
    matcher.add("DEGREE", [nlp.make_doc(d) for d in DEGREE_VOCAB])
    return matcher


def auto_tag(nlp, matcher, text: str) -> list[tuple[str, str]]:
    doc = nlp(text)
    tags = ["O"] * len(doc)

    for match_id, start, end in matcher(doc):
        label = nlp.vocab.strings[match_id]
        if tags[start] != "O":
            continue  # don't overwrite an earlier, longer match
        tags[start] = f"B-{label}"
        for i in range(start + 1, end):
            tags[i] = f"I-{label}"

    # GPA and CERT via regex over the raw text, then map char spans back to
    # tokens. Regex runs after the PhraseMatcher pass and only fills tokens
    # still tagged "O", so it never overwrites a PhraseMatcher match.
    for pattern, label in [(GPA_PATTERN, "GPA"), (CERT_REGEX, "CERT")]:
        for m in pattern.finditer(text):
            span = doc.char_span(m.start(), m.end(), alignment_mode="expand")
            if span is None or tags[span.start] != "O":
                continue
            tags[span.start] = f"B-{label}"
            for i in range(span.start + 1, span.end):
                if i < len(tags) and tags[i] == "O":
                    tags[i] = f"I-{label}"

    return list(zip([t.text for t in doc], tags))


def to_bio_jsonl(tagged_examples: list[list[tuple[str, str]]], out_path: Path) -> None:
    with open(out_path, "w") as f:
        for tokens_tags in tagged_examples:
            if not tokens_tags:
                continue
            tokens, tags = zip(*tokens_tags)
            f.write(json.dumps({"tokens": list(tokens), "ner_tags": list(tags)}) + "\n")


def main():
    nlp = spacy.load("en_core_web_sm")
    matcher = build_matcher(nlp)

    resumes = pd.read_csv(RAW_DIR / "kaggle_resumes" / "UpdatedResumeDataSet.csv")
    resumes = resumes.dropna(subset=["Resume"]).reset_index(drop=True)

    # Stratify: GPA/CGPA mentions are rare in this corpus (26 of 962 resumes)
    # — a plain random sample risks landing under the validation threshold by
    # bad luck alone, not because the entity is truly absent. Force every
    # GPA-bearing resume into the gold set, then fill the rest randomly.
    has_gpa = resumes["Resume"].apply(lambda t: bool(GPA_PATTERN.search(t)))
    gpa_rows = resumes[has_gpa]
    remaining_pool = resumes[~has_gpa]
    fill_count = max(GOLD_SAMPLE_SIZE - len(gpa_rows), 0)
    gold_df = pd.concat([gpa_rows, remaining_pool.sample(n=fill_count, random_state=SEED)])
    silver_df = resumes.drop(gold_df.index)

    print(f"Tagging {len(gold_df)} gold candidates + {len(silver_df)} silver resumes...")

    gold_tagged = [auto_tag(nlp, matcher, text) for text in gold_df["Resume"]]
    silver_tagged = [auto_tag(nlp, matcher, text) for text in silver_df["Resume"]]

    to_bio_jsonl(gold_tagged, OUT_DIR / "gold_val_test.jsonl")
    to_bio_jsonl(silver_tagged, OUT_DIR / "silver_train.jsonl")

    # Human-readable export of the gold set for the actual manual-correction
    # pass (see docstring / Phase 3 doc §5.3 step 3 — a spreadsheet works at
    # this scale, or import into doccano for a proper tagging UI).
    gold_review_rows = []
    for (_, row), tagged in zip(gold_df.iterrows(), gold_tagged):
        entities = [(tok, tag) for tok, tag in tagged if tag != "O"]
        gold_review_rows.append(
            {
                "category": row["Category"],
                "resume_text": row["Resume"],
                "auto_tagged_entities": "; ".join(f"{tok}[{tag}]" for tok, tag in entities),
            }
        )
    pd.DataFrame(gold_review_rows).to_csv(OUT_DIR / "gold_review.csv", index=False)

    # Validation checklist (docs/phases/MENTORA_Phase3_Datasets.md §5.5)
    from collections import Counter

    entity_counts = Counter()
    for tagged in gold_tagged:
        for _, tag in tagged:
            if tag.startswith("B-"):
                entity_counts[tag[2:]] += 1

    print("\nEntity counts in gold set (need >= 20 each):")
    for entity_type in ["SKILL", "CERT", "GPA", "DEGREE"]:
        count = entity_counts.get(entity_type, 0)
        flag = "OK" if count >= 20 else "LOW"
        print(f"  {entity_type}: {count} [{flag}]")

    print(f"\nSaved to {OUT_DIR}")
    print("  - gold_val_test.jsonl  <- NOT reviewed yet, see gold_review.csv")
    print("  - silver_train.jsonl   <- auto-tagged, used as-is for training")
    print("  - gold_review.csv      <- human-readable, for the manual correction pass")


if __name__ == "__main__":
    main()
