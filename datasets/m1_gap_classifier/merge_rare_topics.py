"""
M1 — merge rare heuristic topic classes into their subject's General bucket.

tag_topics.py's keyword heuristic produced 30 topic classes ranging from 381
examples down to 3 (Reading Comprehension) — attempt 1's F1 (micro) came in
at 0.4352 vs the >=0.85 target, and a class with 3 training examples can't
be fixed by hyperparameters. This folds any topic with fewer than
MIN_EXAMPLES rows into "General <Subject>" for that row's subject, which
keeps every surviving class in question_bank_final.csv above the threshold.
Math rows (real topics from the Kaggle source, not heuristic) are also
subject to this merge if they happen to be sparse, same rule applied
uniformly.

Run: ~/.venvs/mentora-data/bin/python datasets/m1_gap_classifier/merge_rare_topics.py
Output: mentora_data/processed/m1/question_bank_final.csv (topic column
        updated in place; subtopic untouched)
"""

from pathlib import Path

import pandas as pd

M1_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m1"
MIN_EXAMPLES = 25


def main():
    path = M1_DIR / "question_bank_final.csv"
    df = pd.read_csv(path)

    counts = df["topic"].value_counts()
    rare_topics = set(counts[counts < MIN_EXAMPLES].index)
    print(f"Merging {len(rare_topics)} rare topics (<{MIN_EXAMPLES} examples): {sorted(rare_topics)}")

    def merge_one(row):
        if row["topic"] in rare_topics:
            return f"General {row['subject']}"
        return row["topic"]

    df["topic"] = df.apply(merge_one, axis=1)
    df.to_csv(path, index=False)
    print(f"Saved to {path}")

    print(f"\nNew topic distribution ({df['topic'].nunique()} classes):")
    print(df["topic"].value_counts())


if __name__ == "__main__":
    main()
