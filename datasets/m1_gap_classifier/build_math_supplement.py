"""
M1 dataset supplement — Mathematics.

MDCAT (the 23 real past papers) doesn't test Mathematics at all, so it can't
cover the general "university entry test" group's Math requirement on its
own. This converts a real, labeled Kaggle dataset into the same schema as
extract_questions.py's MDCAT output, ready to concatenate together.

Source: Kaggle "College Readiness Math Questions Dataset"
(k5m1th/college-readiness-math-questions-dataset, CC-BY-SA-4.0). 434
SAT-style college-readiness math questions, real correct answers, and
existing domain/subtopic labels (Algebra, Advanced Math, Problem-Solving and
Data Analysis, Geometry and Trigonometry) — no manual tagging needed, unlike
the MDCAT extraction.

Run: ~/.venvs/mentora-data/bin/python datasets/m1_gap_classifier/build_math_supplement.py
Output: mentora_data/processed/m1/math_supplement.csv
"""

import ast
import csv
from pathlib import Path

import pandas as pd

RAW_PATH = (
    Path(__file__).resolve().parents[2]
    / "mentora_data" / "raw" / "kaggle_general_mcq" / "college_readiness_math"
    / "College Readiness Math Questions Dataset_train.csv"
)
OUT_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m1"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    df = pd.read_csv(RAW_PATH)
    df = df.dropna(subset=["question", "correct_answer"])
    before = len(df)
    df = df.drop_duplicates(subset=["question"])
    if before != len(df):
        print(f"Dropped {before - len(df)} exact-duplicate questions from the source dataset")

    rows = []
    for _, r in df.iterrows():
        options = {"A": r["choice_A"], "B": r["choice_B"], "C": r["choice_C"], "D": r["choice_D"]}
        rows.append(
            {
                "source": "kaggle_college_readiness_math",
                "subject": "Mathematics",
                "topic": r["domain"],
                "subtopic": r["label"],
                "difficulty": "",  # not provided by source — still a TODO
                "question_text": r["question"],
                "options": options,
                "correct_answer": r["correct_answer"],
            }
        )

    print(f"Converted {len(rows)} math questions")
    print(df["domain"].value_counts())

    out_path = OUT_DIR / "math_supplement.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["question_id", "source", "subject", "topic", "subtopic", "difficulty", "question_text", "options", "correct_answer"]
        )
        for i, row in enumerate(rows, 1):
            writer.writerow(
                [
                    i,
                    row["source"],
                    row["subject"],
                    row["topic"],
                    row["subtopic"],
                    row["difficulty"],
                    row["question_text"],
                    str(row["options"]),
                    row["correct_answer"],
                ]
            )
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
