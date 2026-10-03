"""
M1 dataset — synthetic answer sessions (docs/phases/MENTORA_Phase3_Datasets.md §4.5).

M1 needs labeled examples of "this pattern of wrong answers implies weak in
topic X." Real student answer history doesn't exist yet (no real users), so
— per the doc — generate synthetic answer sessions ON TOP OF the real,
correctly-sourced question bank: the QUESTIONS are real (MDCAT + the Kaggle
math set), the SESSIONS (who answered what, right or wrong) are simulated.
This is the same "synthetic is fine for the cold-start problem" reasoning
already used for M3.

Each synthetic student gets a hidden per-topic "strength" (0=weak..1=strong);
their simulated correctness on each sampled question is a coin flip weighted
by their strength in that question's subject.

Run: ~/.venvs/mentora-data/bin/python datasets/m1_gap_classifier/generate_synthetic_sessions.py
Output: mentora_data/processed/m1/synthetic_answer_sessions.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

M1_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m1"
N_STUDENTS = 500
QUESTIONS_PER_STUDENT = (15, 30)
SEED = 11


def main():
    questions = pd.read_csv(M1_DIR / "question_bank_final.csv")
    subjects = questions["subject"].unique()
    rng = np.random.default_rng(SEED)

    sessions = []
    for student_id in range(1, N_STUDENTS + 1):
        subject_strength = {s: rng.uniform(0, 1) for s in subjects}
        n = rng.integers(*QUESTIONS_PER_STUDENT)
        sampled = questions.sample(n=n, random_state=student_id)
        for _, q in sampled.iterrows():
            p_correct = subject_strength[q["subject"]]
            is_correct = bool(rng.uniform() < p_correct)
            sessions.append(
                {
                    "student_id": student_id,
                    "question_id": q["question_id"],
                    "subject": q["subject"],
                    "topic": q["topic"] if pd.notna(q["topic"]) and q["topic"] != "" else q["subject"],
                    "is_correct": is_correct,
                }
            )

    df = pd.DataFrame(sessions)
    out_path = M1_DIR / "synthetic_answer_sessions.csv"
    df.to_csv(out_path, index=False)

    print(f"Generated {len(df)} synthetic answer records for {N_STUDENTS} students")
    print(f"Saved to {out_path}")

    # Validation checklist (docs/phases/MENTORA_Phase3_Datasets.md §4.6)
    print("\nPer-subject mean correctness (sanity check — should vary, not be uniform):")
    print(df.groupby("subject")["is_correct"].mean())


if __name__ == "__main__":
    main()
