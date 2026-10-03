"""
M2 dataset — Adaptive Question Generator (docs/phases/MENTORA_Phase3_Datasets.md §6).

Reuses M1's question bank, reshaped into (prompt, target) pairs for FLAN-T5
fine-tuning: `(topic, difficulty) -> generated question + options + answer`.
No new sourcing needed — this is why M1 was built first.

`difficulty` isn't set on most M1 rows (MDCAT extraction never did manual
per-question tagging — see mentora_data/SOURCES.md; the Math supplement
doesn't carry it either). Per the doc §6.3, a heuristic first pass is an
accepted trade-off when hand-tagging a bank this size isn't time-boxed:
shorter, single-clause questions -> easy; longer or multi-step ones -> hard.
This is a proxy, not ground truth — spot-check before trusting it fully.

Run: ~/.venvs/mentora-data/bin/python datasets/m2_question_generator/build_training_data.py
Output: mentora_data/processed/m2/flan_t5_training_data.csv
"""

import ast
import json
from pathlib import Path

import pandas as pd

M1_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m1"
OUT_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MULTI_STEP_MARKERS = ["calculate", "if", "then", "given that", "what will be", "find the value"]


def heuristic_difficulty(text: str) -> str:
    text_lower = str(text).lower()
    word_count = len(text_lower.split())
    multi_step = any(marker in text_lower for marker in MULTI_STEP_MARKERS)
    if word_count < 12 and not multi_step:
        return "easy"
    if word_count > 30 or multi_step:
        return "hard"
    return "medium"


def main():
    questions = pd.read_csv(M1_DIR / "question_bank_final.csv")
    questions = questions.dropna(subset=["question_text"])

    # Fill in missing difficulty with the heuristic; keep any real values
    # (the Math supplement has none, MDCAT rows have none — so this applies
    # to effectively every row right now, which is the honest state to flag).
    questions["difficulty"] = questions["difficulty"].astype(object)
    missing_difficulty = questions["difficulty"].isna() | (questions["difficulty"] == "")
    questions.loc[missing_difficulty, "difficulty"] = questions.loc[missing_difficulty, "question_text"].apply(
        heuristic_difficulty
    )
    print(f"Difficulty heuristically assigned for {missing_difficulty.sum()} of {len(questions)} rows")

    rows = []
    skipped_bad_json = 0
    for _, r in questions.iterrows():
        try:
            options = ast.literal_eval(r["options"])
        except (ValueError, SyntaxError):
            skipped_bad_json += 1
            continue
        if not isinstance(options, dict) or len(options) < 2:
            skipped_bad_json += 1
            continue

        topic_label = r["topic"] if pd.notna(r["topic"]) and r["topic"] != "" else r["subject"]
        subtopic_label = r["subtopic"] if pd.notna(r["subtopic"]) and r["subtopic"] != "" else None
        topic_desc = f"{topic_label} ({subtopic_label})" if subtopic_label else topic_label

        prompt = f"Generate a {r['difficulty']} difficulty multiple-choice question about {topic_desc}."
        target = {
            "question": r["question_text"],
            "options": options,
            "correct_answer": r["correct_answer"] if pd.notna(r["correct_answer"]) and r["correct_answer"] != "" else None,
        }

        target_json = json.dumps(target)
        # Validate it round-trips cleanly (doc §6.4 checklist) before saving.
        json.loads(target_json)

        rows.append({"input_text": prompt, "target_text": target_json, "subject": r["subject"]})

    out_df = pd.DataFrame(rows)
    out_path = OUT_DIR / "flan_t5_training_data.csv"
    out_df.to_csv(out_path, index=False)

    print(f"\nSkipped {skipped_bad_json} rows with malformed options")
    print(f"Built {len(out_df)} prompt/target pairs -> {out_path}")

    # Validation checklist (docs/phases/MENTORA_Phase3_Datasets.md §6.4)
    print(f"\n[{'OK' if len(out_df) >= 500 else 'LOW'}] total pairs: {len(out_df)} (target: >=500)")
    print("\nDifficulty spread:")
    print(questions["difficulty"].value_counts())
    print("\nSample:")
    print(out_df.sample(2, random_state=1).to_string())


if __name__ == "__main__":
    main()
