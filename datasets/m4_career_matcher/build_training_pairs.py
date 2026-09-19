"""
M4 dataset, part 2 — Career-Skill Semantic Matcher: training pairs.

Source: Kaggle "Job Descriptions 2025 - Tech & Non-Tech Roles"
(adityarajsrv/job-descriptions-2025-tech-and-non-tech-roles, CC BY 4.0).
1068 postings, 218 unique titles, zero missing skills — this is the
resume-style technical vocabulary (Python, SQL, React, ...) that O*NET's
generic skill list (part 1) doesn't have.

Positive pairs: a posting's own (skills, title) — a real match.
Negative pairs: the same skills shuffled against a different random title —
teaches the model what a mismatch looks like, per
docs/phases/MENTORA_Phase3_Datasets.md §3.3.

Run: ~/.venvs/mentora-data/bin/python datasets/m4_career_matcher/build_training_pairs.py
Output: mentora_data/processed/m4/training_pairs.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "raw" / "kaggle_job_postings"
OUT_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m4"
OUT_DIR.mkdir(parents=True, exist_ok=True)

jobs = pd.read_csv(RAW_DIR / "job_dataset.csv")
jobs = jobs.rename(columns={"Title": "job_title", "Skills": "required_skills"})[["job_title", "required_skills"]].dropna()

positive_pairs = jobs.copy()
positive_pairs["label"] = 1.0

rng = np.random.default_rng(7)
shuffled_titles = jobs["job_title"].sample(frac=1, random_state=7).reset_index(drop=True)
# Guard against a shuffle accidentally re-pairing a title with itself (common
# when one title dominates the dataset) — reroll those rows once.
same_as_original = (shuffled_titles.values == jobs["job_title"].values)
if same_as_original.any():
    reroll = jobs.loc[same_as_original, "job_title"].sample(frac=1, random_state=8).values
    shuffled_titles.loc[same_as_original] = reroll

negative_pairs = pd.DataFrame(
    {
        "job_title": shuffled_titles,
        "required_skills": jobs["required_skills"].values,
        "label": 0.0,
    }
)

pairs = pd.concat([positive_pairs, negative_pairs], ignore_index=True).sample(frac=1, random_state=7).reset_index(drop=True)

# Validation checklist (docs/phases/MENTORA_Phase3_Datasets.md §3.4)
label_counts = pairs["label"].value_counts(normalize=True)
print("Label distribution:")
print(label_counts)
assert abs(label_counts[1.0] - label_counts[0.0]) < 0.02, "Label split isn't close to 50/50"

pairs.to_csv(OUT_DIR / "training_pairs.csv", index=False)
print(f"\nBuilt {len(pairs)} training pairs -> {OUT_DIR / 'training_pairs.csv'}")
print("\nSpot-check 5 positive pairs (should plausibly belong to that title):")
print(positive_pairs.sample(5, random_state=1)[["job_title", "required_skills"]].to_string(index=False))
