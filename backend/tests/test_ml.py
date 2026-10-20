import pandas as pd

from app.ml.features import MODEL_FEATURES, build_features, feedback_sentiment
from app.services.predictor import get_predictor


def test_sentiment():
    assert feedback_sentiment("Good and attentive") > 0
    assert feedback_sentiment("Irregular and weak") < 0
    assert feedback_sentiment("not regular") < 0
    assert feedback_sentiment("") == 0


def test_build_features_order():
    row = {"attendance_pct": 80, "avg_marks": 60, "prev_marks": 70, "assignment_completion": 70,
           "behavior_score": 70, "failed_subjects": 0, "distance_km": 5, "fee_pending": False,
           "extracurricular": True, "family_income": "Medium", "parent_education": "School",
           "teacher_feedback": "good"}
    f = build_features(pd.DataFrame([row]))
    assert list(f.columns) == MODEL_FEATURES
    assert f["marks_trend"].iloc[0] == -10


def test_model_is_monotonic_in_attendance():
    p = get_predictor()
    base = {"avg_marks": 45, "prev_marks": 50, "assignment_completion": 50, "behavior_score": 55,
            "failed_subjects": 1, "distance_km": 8, "fee_pending": False, "extracurricular": False,
            "family_income": "Medium", "parent_education": "School", "teacher_feedback": ""}
    low = p.predict_one({**base, "attendance_pct": 45})["risk_probability"]
    high = p.predict_one({**base, "attendance_pct": 95})["risk_probability"]
    assert high < low
