"""
M1 dataset — final merge.

Combines the two M1 sources into one question bank:
  - question_bank.csv       (MDCAT extraction: Biology/Chemistry/Physics/
                              English/Logical Reasoning — real past papers,
                              correct_answer still blank, needs manual entry)
  - math_supplement.csv     (Kaggle college-readiness math — Mathematics,
                              real correct_answer + subtopic already present)

Together these cover the platform's full subject set for both MDCAT and the
general university-entry-test group (Math/Physics/Chemistry/English).

Run: ~/.venvs/mentora-data/bin/python datasets/m1_gap_classifier/merge_question_bank.py
Output: mentora_data/processed/m1/question_bank_final.csv
"""

import csv
from pathlib import Path

import pandas as pd

M1_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m1"


def main():
    mdcat = pd.read_csv(M1_DIR / "question_bank.csv")
    math = pd.read_csv(M1_DIR / "math_supplement.csv")

    combined = pd.concat([mdcat, math], ignore_index=True)
    combined["question_id"] = range(1, len(combined) + 1)

    out_path = M1_DIR / "question_bank_final.csv"
    combined.to_csv(out_path, index=False, quoting=csv.QUOTE_ALL)

    print(f"MDCAT questions: {len(mdcat)}")
    print(f"Math supplement: {len(math)}")
    print(f"Combined total: {len(combined)}")
    print("\nBy subject:")
    print(combined["subject"].value_counts())
    print(f"\nSaved to {out_path}")

    print("\nValidation checklist (docs/phases/MENTORA_Phase3_Datasets.md §4.6):")
    for subject, count in combined["subject"].value_counts().items():
        flag = "OK" if count >= 30 else "LOW"
        print(f"  {subject}: {count} [{flag}] (target: >=30 for a usable topic, 150-300 ideal)")

    missing_answers = combined["correct_answer"].isna().sum() + (combined["correct_answer"] == "").sum()
    print(f"\nRows still missing correct_answer: {missing_answers} of {len(combined)} (all MDCAT rows — see SOURCES.md)")


if __name__ == "__main__":
    main()
