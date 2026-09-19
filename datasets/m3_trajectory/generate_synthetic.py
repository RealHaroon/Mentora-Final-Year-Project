"""
M3 dataset — Performance Trajectory Predictor.

Synthetic per-student score histories. Synthetic data is explicitly acceptable
here (per docs/phases/MENTORA_Phase3_Datasets.md §2.1) since the LSTM only
needs to learn the general *shape* of trajectories (rising/falling/plateauing/
noisy), not memorize real students — Mentora has no real user history yet.

Run: ~/.venvs/mentora-data/bin/python datasets/m3_trajectory/generate_synthetic.py
Output: mentora_data/processed/m3/score_histories.csv (with archetype, for
        your own validation/plots) and score_histories_no_label.csv (the
        actual LSTM training input — archetype is the "answer key", so the
        model must not see it).
"""

from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m3"
OUT_DIR.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(42)
N_STUDENTS = 800
SESSIONS_PER_STUDENT = (8, 20)  # min, max — varies per student, like real usage
ARCHETYPES = ["improving", "declining", "plateau", "volatile"]

rows = []
for student_id in range(1, N_STUDENTS + 1):
    n_sessions = rng.integers(*SESSIONS_PER_STUDENT)
    archetype = rng.choice(ARCHETYPES)
    base = rng.uniform(40, 70)

    scores = []
    for s in range(n_sessions):
        if archetype == "improving":
            trend = base + s * rng.uniform(1.0, 2.5)
        elif archetype == "declining":
            trend = base - s * rng.uniform(0.5, 1.5)
        elif archetype == "plateau":
            trend = base + min(s, 5) * rng.uniform(1.0, 2.0)  # rises then flattens
        else:  # volatile
            trend = base + rng.uniform(-15, 15)
        noise = rng.normal(0, 4)
        score = float(np.clip(trend + noise, 0, 100))
        scores.append(score)

    for s, score in enumerate(scores):
        rows.append(
            {
                "student_id": student_id,
                "session_number": s + 1,
                "score": round(score, 1),
                "archetype": archetype,
            }
        )

df = pd.DataFrame(rows)

# Validation checklist (docs/phases/MENTORA_Phase3_Datasets.md §2.3)
counts = df.groupby("archetype")["student_id"].nunique()
print("Students per archetype:")
print(counts)
assert counts.min() >= counts.max() / 2, "Archetype representation too skewed"
assert df["score"].between(0, 100).all(), "Scores out of [0, 100] range"

# Drop any student with fewer than 5 sessions — LSTM needs a minimum sequence
# length to learn anything.
sessions_per_student = df.groupby("student_id").size()
too_short = sessions_per_student[sessions_per_student < 5].index
if len(too_short) > 0:
    print(f"Dropping {len(too_short)} students with fewer than 5 sessions")
    df = df[~df["student_id"].isin(too_short)]

df.to_csv(OUT_DIR / "score_histories.csv", index=False)
df.drop(columns=["archetype"]).to_csv(OUT_DIR / "score_histories_no_label.csv", index=False)

print(f"\nSaved {len(df)} rows across {df['student_id'].nunique()} students to {OUT_DIR}")
print("  - score_histories.csv            (with archetype, for your own eyeballing/plots)")
print("  - score_histories_no_label.csv   (actual LSTM training input)")
