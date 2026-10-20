"""
Trains the dropout model and writes artifacts/model.joblib + metrics.json.

    python -m app.ml.train
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, fbeta_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import (RandomizedSearchCV, StratifiedKFold, cross_val_predict,
                                     cross_validate, train_test_split)
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from app.ml.features import CATEGORY_VALUES, MODEL_CATEGORICAL, MODEL_NUMERIC, build_features
from app.ml.generate_data import DATA_PATH, generate

ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "model.joblib"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"
SEED = 42


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", StandardScaler(), MODEL_NUMERIC),
        ("cat", OneHotEncoder(categories=[CATEGORY_VALUES[c] for c in MODEL_CATEGORICAL],
                              handle_unknown="ignore"), MODEL_CATEGORICAL),
    ])


def make_pipeline(model) -> Pipeline:
    return Pipeline([
        ("prep", make_preprocessor()),
        ("smote", SMOTE(random_state=SEED)),
        ("model", model),
    ])


def evaluate(y_true, proba, threshold) -> dict:
    pred = (proba >= threshold).astype(int)
    return {
        "accuracy": round(accuracy_score(y_true, pred), 4),
        "precision": round(precision_score(y_true, pred), 4),
        "recall": round(recall_score(y_true, pred), 4),
        "f1": round(f1_score(y_true, pred), 4),
        "f2": round(fbeta_score(y_true, pred, beta=2), 4),
        "roc_auc": round(roc_auc_score(y_true, proba), 4),
    }


def main():
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate().to_csv(DATA_PATH, index=False)

    raw = pd.read_csv(DATA_PATH)
    X, y = build_features(raw), raw["dropout"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

    # baselines
    candidates = {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "Random Forest": RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1),
        "XGBoost": XGBClassifier(eval_metric="logloss", random_state=SEED, n_jobs=-1),
    }
    comparison = []
    for name, model in candidates.items():
        scores = cross_validate(make_pipeline(model), X_train, y_train, cv=cv,
                                scoring=["roc_auc", "f1", "recall", "precision"])
        row = {"model": name, **{m: round(scores[f"test_{m}"].mean(), 4)
                                 for m in ["roc_auc", "f1", "recall", "precision"]}}
        comparison.append(row)
        print(f"{name:20s} AUC={row['roc_auc']:.3f}  F1={row['f1']:.3f}  Recall={row['recall']:.3f}")

    search = RandomizedSearchCV(
        make_pipeline(XGBClassifier(eval_metric="logloss", random_state=SEED, n_jobs=-1)),
        param_distributions={
            "model__n_estimators": [100, 200, 300, 400],
            "model__max_depth": [2, 3, 4, 5, 6],
            "model__learning_rate": [0.01, 0.03, 0.05, 0.1, 0.2],
            "model__subsample": [0.7, 0.8, 0.9, 1.0],
            "model__colsample_bytree": [0.6, 0.8, 1.0],
            "model__min_child_weight": [1, 3, 5],
        },
        # XGBoost is already multi-threaded; nested joblib workers crashed on Windows
        n_iter=25, scoring="roc_auc", cv=cv, random_state=SEED, n_jobs=1,
    )
    search.fit(X_train, y_train)
    best = search.best_estimator_
    print(f"Best CV AUC (tuned XGBoost): {search.best_score_:.4f}")

    # Pick the threshold on out-of-fold predictions. F2 because a missed dropout
    # is worse than a false alarm.
    oof = cross_val_predict(best, X_train, y_train, cv=cv, method="predict_proba")[:, 1]
    thresholds = np.arange(0.2, 0.71, 0.02)
    threshold = float(thresholds[np.argmax([fbeta_score(y_train, oof >= t, beta=2) for t in thresholds])])

    proba = best.predict_proba(X_test)[:, 1]
    test_metrics = evaluate(y_test, proba, threshold)
    tn, fp, fn, tp = confusion_matrix(y_test, proba >= threshold).ravel()
    fpr, tpr, _ = roc_curve(y_test, proba)
    idx = np.linspace(0, len(fpr) - 1, 40).astype(int)
    print("Test metrics:", test_metrics, "threshold:", round(threshold, 2))

    # gain importance, one-hot columns merged back into their feature
    names = best.named_steps["prep"].get_feature_names_out()
    gains = best.named_steps["model"].feature_importances_
    importance: dict[str, float] = {}
    for n, g in zip(names, gains):
        base = n.split("__", 1)[1]
        for cat in MODEL_CATEGORICAL:
            if base.startswith(cat + "_"):
                base = cat
        importance[base] = importance.get(base, 0) + float(g)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    version = datetime.now(timezone.utc).strftime("xgb-%Y%m%d-%H%M")
    joblib.dump({"pipeline": best, "threshold": threshold, "version": version}, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps({
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {"rows": len(raw), "dropout_rate": round(float(y.mean()), 4),
                    "train_rows": len(X_train), "test_rows": len(X_test)},
        "comparison": comparison,
        "best_params": {k.replace("model__", ""): v for k, v in search.best_params_.items()},
        "cv_auc": round(search.best_score_, 4),
        "threshold": round(threshold, 2),
        "test": test_metrics,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "roc_curve": [{"fpr": round(float(fpr[i]), 3), "tpr": round(float(tpr[i]), 3)} for i in idx],
        "feature_importance": dict(sorted(((k, round(v, 4)) for k, v in importance.items()),
                                          key=lambda kv: -kv[1])),
    }, indent=2))
    print(f"Saved model -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
