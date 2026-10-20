"""
Synthetic student dataset.

Real student records aren't publicly available, so this simulates the risk
factors reported in dropout studies (attendance, failures, fee stress, distance...)
with a few non-linear effects and noise.

    python -m app.ml.generate_data
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "students.csv"

POSITIVE_REMARKS = [
    "Good and attentive in class", "Hardworking and sincere student",
    "Regular and punctual, participates actively", "Bright student, consistent effort",
    "Improving steadily, more confident now", "Excellent focus and helpful to others",
]
NEUTRAL_REMARKS = [
    "Average performance this term", "Needs to revise more at home",
    "Quiet student", "Can do better with practice", "",
]
NEGATIVE_REMARKS = [
    "Irregular and often absent", "Weak in basics, struggling with subjects",
    "Seems distracted and demotivated", "Not regular with homework",
    "Marks declining, family problems reported", "Often late and disinterested",
]


def generate(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # latent engagement drives most of the observed scores
    engagement = rng.beta(4, 2, n)

    attendance = np.clip(engagement * 100 + rng.normal(0, 12, n), 20, 100)
    prev_marks = np.clip(engagement * 85 + rng.normal(5, 12, n), 10, 100)
    avg_marks = np.clip(prev_marks + rng.normal(0, 8, n) - (engagement < 0.45) * rng.uniform(0, 12, n), 5, 100)
    assignment = np.clip(engagement * 100 + rng.normal(0, 15, n), 0, 100)
    behavior = np.clip(engagement * 80 + rng.normal(15, 12, n), 10, 100)
    failed = np.clip(np.round((60 - avg_marks) / 12 + rng.normal(0, 0.8, n)), 0, 6)
    distance = np.round(np.clip(rng.gamma(2, 3.5, n), 0.5, 30), 1)
    income = rng.choice(["Low", "Medium", "High"], n, p=[0.35, 0.45, 0.20])
    parent_edu = rng.choice(["None", "School", "Graduate"], n, p=[0.20, 0.50, 0.30])
    fee_pending = (rng.random(n) < np.where(income == "Low", 0.35, np.where(income == "Medium", 0.12, 0.04))).astype(int)
    extracurricular = (rng.random(n) < 0.15 + 0.4 * engagement).astype(int)

    logit = (
        -2.9
        - 0.01 * (attendance - 75)
        + 1.2 * (attendance < 60)                       # sharp jump below 60% attendance
        - 0.02 * (avg_marks - 55)
        - 0.03 * (avg_marks - prev_marks)
        - 0.01 * (assignment - 65)
        - 0.008 * (behavior - 65)
        + 0.22 * failed
        + 0.25 * fee_pending
        + 1.0 * fee_pending * (income == "Low")         # financial stress compounds
        + 0.025 * (distance - 7)
        + np.where(income == "Low", 0.25, np.where(income == "High", -0.2, 0))
        + np.where(parent_edu == "None", 0.2, np.where(parent_edu == "Graduate", -0.15, 0))
        - 0.3 * extracurricular
        + 0.9 * (failed >= 2) * (avg_marks < prev_marks)  # failing AND getting worse
        + rng.normal(0, 0.8, n)                         # things we can't measure
    )
    dropout = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)

    # Remarks depend on the risk score, not on the sampled outcome (avoids leakage)
    def remark(e, risk):
        r = rng.random()
        if risk > -1.5 and r < 0.5 or e < 0.4 and r < 0.4:
            return rng.choice(NEGATIVE_REMARKS)
        if e > 0.7 and r < 0.6:
            return rng.choice(POSITIVE_REMARKS)
        return rng.choice(NEUTRAL_REMARKS + POSITIVE_REMARKS[:2] + NEGATIVE_REMARKS[:1])

    feedback = [remark(e, risk) for e, risk in zip(engagement, logit)]

    return pd.DataFrame({
        "attendance_pct": attendance.round(1),
        "avg_marks": avg_marks.round(1),
        "prev_marks": prev_marks.round(1),
        "assignment_completion": assignment.round(1),
        "behavior_score": behavior.round(1),
        "failed_subjects": failed.astype(int),
        "distance_km": distance,
        "fee_pending": fee_pending,
        "extracurricular": extracurricular,
        "family_income": income,
        "parent_education": parent_edu,
        "teacher_feedback": feedback,
        "dropout": dropout,
    })


if __name__ == "__main__":
    df = generate()
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    print(f"Saved {len(df)} rows to {DATA_PATH}")
    print(f"Dropout rate: {df['dropout'].mean():.1%}")
