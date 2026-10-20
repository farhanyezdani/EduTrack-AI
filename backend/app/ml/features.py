"""Feature engineering used by both training and the API (keeps them in sync)."""
import re

import pandas as pd

NUMERIC_INPUTS = [
    "attendance_pct",         # 0-100
    "avg_marks",              # 0-100, current term
    "prev_marks",             # 0-100, previous term
    "assignment_completion",  # 0-100
    "behavior_score",         # 0-100
    "failed_subjects",        # 0-6
    "distance_km",            # home to school
]
BINARY_INPUTS = ["fee_pending", "extracurricular"]
CATEGORICAL_INPUTS = ["family_income", "parent_education"]

CATEGORY_VALUES = {
    "family_income": ["Low", "Medium", "High"],
    "parent_education": ["None", "School", "Graduate"],
}

ENGINEERED = ["marks_trend", "feedback_sentiment"]

MODEL_NUMERIC = NUMERIC_INPUTS + BINARY_INPUTS + ENGINEERED
MODEL_CATEGORICAL = CATEGORICAL_INPUTS
MODEL_FEATURES = MODEL_NUMERIC + MODEL_CATEGORICAL

FEATURE_LABELS = {
    "attendance_pct": "Attendance",
    "avg_marks": "Average marks",
    "prev_marks": "Previous term marks",
    "assignment_completion": "Assignment completion",
    "behavior_score": "Behaviour score",
    "failed_subjects": "Failed subjects",
    "distance_km": "Distance from school",
    "fee_pending": "Fee pending",
    "extracurricular": "Extracurricular activity",
    "marks_trend": "Marks trend (vs last term)",
    "feedback_sentiment": "Teacher feedback tone",
    "family_income": "Family income",
    "parent_education": "Parent education",
}

# Lexicon-based sentiment for teacher remarks
NEGATIVE_WORDS = {
    "irregular", "absent", "weak", "poor", "struggling", "distracted", "lazy",
    "disinterested", "uninterested", "late", "fails", "failing", "careless",
    "withdrawn", "demotivated", "unmotivated", "bunks", "skips", "rude",
    "worried", "problem", "problems", "issues", "decline", "declining", "dropping",
}
POSITIVE_WORDS = {
    "good", "excellent", "regular", "attentive", "hardworking", "sincere",
    "improving", "improved", "active", "confident", "punctual", "consistent",
    "motivated", "bright", "helpful", "participates", "focused", "great",
}
NEGATORS = {"not", "no", "never", "hardly", "rarely"}


def feedback_sentiment(text: str | None) -> float:
    """Score in [-1, 1]. A negator right before a word flips it ("not regular")."""
    if not text:
        return 0.0
    words = re.findall(r"[a-z]+", text.lower())
    score, hits = 0, 0
    for i, word in enumerate(words):
        polarity = 1 if word in POSITIVE_WORDS else -1 if word in NEGATIVE_WORDS else 0
        if polarity == 0:
            continue
        if i > 0 and words[i - 1] in NEGATORS:
            polarity = -polarity
        score += polarity
        hits += 1
    return round(score / hits, 3) if hits else 0.0


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["marks_trend"] = out["avg_marks"] - out["prev_marks"]
    out["feedback_sentiment"] = out["teacher_feedback"].fillna("").map(feedback_sentiment)
    for col in BINARY_INPUTS:
        out[col] = out[col].astype(int)
    return out[MODEL_FEATURES]
