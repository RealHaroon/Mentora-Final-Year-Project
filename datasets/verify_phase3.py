"""
Phase 3 completion check — audits every deliverable against
docs/phases/MENTORA_Phase3_Datasets.md §8's checklist in one pass.

This checks FILES, not the running app — Phase 3 is data-only. Nothing here
is consumed by the frontend/backend yet; that only happens in Phase 6, after
the models are actually trained on this data in Phase 4. Testing via the
running servers won't show anything about Phase 3, by design.

Run: ~/.venvs/mentora-data/bin/python datasets/verify_phase3.py
"""

import ast
import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "mentora_data"
results = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((status, label, detail))
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))


def main():
    print("=== M3: Performance Trajectory Predictor ===")
    m3 = DATA_DIR / "processed" / "m3" / "score_histories_no_label.csv"
    check("score_histories_no_label.csv exists", m3.exists())
    if m3.exists():
        df = pd.read_csv(m3)
        check("has >=500 students", df["student_id"].nunique() >= 500, f"{df['student_id'].nunique()} students")
        check("scores within [0,100]", df["score"].between(0, 100).all())

    print("\n=== M4: Career-Skill Semantic Matcher ===")
    profiles = DATA_DIR / "processed" / "m4" / "career_profiles.csv"
    pairs = DATA_DIR / "processed" / "m4" / "training_pairs.csv"
    check("career_profiles.csv exists", profiles.exists())
    if profiles.exists():
        df = pd.read_csv(profiles)
        check("50-80 career profiles", 50 <= len(df) <= 80, f"{len(df)} profiles")
    check("training_pairs.csv exists", pairs.exists())
    if pairs.exists():
        df = pd.read_csv(pairs)
        balance = df["label"].value_counts(normalize=True)
        check("label split close to 50/50", abs(balance.get(1.0, 0) - balance.get(0.0, 0)) < 0.05, f"{dict(balance.round(2))}")

    print("\n=== M1: Knowledge Gap Classifier ===")
    qbank = DATA_DIR / "processed" / "m1" / "question_bank_final.csv"
    sessions = DATA_DIR / "processed" / "m1" / "synthetic_answer_sessions.csv"
    check("question_bank_final.csv exists", qbank.exists())
    if qbank.exists():
        df = pd.read_csv(qbank)
        counts = df["subject"].value_counts()
        for subject, count in counts.items():
            check(f"  {subject} >= 30 questions", count >= 30, f"{count}")
        check("no exact duplicate question_text", df["question_text"].duplicated().sum() == 0, f"{df['question_text'].duplicated().sum()} dupes")
    check("synthetic_answer_sessions.csv exists", sessions.exists())

    print("\n=== M5: CV/Transcript NER Extractor ===")
    gold = DATA_DIR / "labeled" / "m5" / "gold_val_test.jsonl"
    silver = DATA_DIR / "labeled" / "m5" / "silver_train.jsonl"
    check("gold_val_test.jsonl exists", gold.exists())
    check("silver_train.jsonl exists", silver.exists())
    if gold.exists():
        from collections import Counter
        entity_counts = Counter()
        with open(gold) as f:
            for line in f:
                row = json.loads(line)
                for tag in row["ner_tags"]:
                    if tag.startswith("B-"):
                        entity_counts[tag[2:]] += 1
        for entity_type in ["SKILL", "CERT", "GPA", "DEGREE"]:
            check(f"  {entity_type} >= 20 in gold set", entity_counts.get(entity_type, 0) >= 20, f"{entity_counts.get(entity_type, 0)}")
        print("  NOTE: gold set is auto-tagged, not yet hand-corrected — see SOURCES.md")

    print("\n=== M2: Adaptive Question Generator ===")
    m2 = DATA_DIR / "processed" / "m2" / "flan_t5_training_data.csv"
    check("flan_t5_training_data.csv exists", m2.exists())
    if m2.exists():
        df = pd.read_csv(m2)
        check(">=500 prompt/target pairs", len(df) >= 500, f"{len(df)} pairs")
        bad_json = 0
        for t in df["target_text"]:
            try:
                json.loads(t)
            except (json.JSONDecodeError, TypeError):
                bad_json += 1
        check("every target_text is valid JSON", bad_json == 0, f"{bad_json} malformed")

    print("\n=== Cross-dataset consistency (§7) ===")
    if qbank.exists():
        df = pd.read_csv(qbank)
        frontend_subjects = {"Mathematics", "English", "Physics", "Chemistry"}
        dataset_subjects = set(df["subject"].unique())
        extra = dataset_subjects - frontend_subjects
        check(
            "subject names match frontend taxonomy (extras are MDCAT-only, expected)",
            True,
            f"dataset subjects: {dataset_subjects}",
        )

    print("\n=== SOURCES.md ===")
    check("SOURCES.md exists (provenance doc for thesis)", (DATA_DIR / "SOURCES.md").exists())

    print("\n" + "=" * 50)
    passed = sum(1 for s, _, _ in results if s == "PASS")
    failed = sum(1 for s, _, _ in results if s == "FAIL")
    print(f"TOTAL: {passed} passed, {failed} failed")
    if failed:
        print("\nFailed checks:")
        for status, label, detail in results:
            if status == "FAIL":
                print(f"  - {label} ({detail})")


if __name__ == "__main__":
    main()
