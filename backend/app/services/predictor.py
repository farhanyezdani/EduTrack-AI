"""Loads the trained pipeline once and returns risk + per-feature SHAP contributions."""
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from app.ml.features import FEATURE_LABELS, MODEL_CATEGORICAL, build_features
from app.ml.train import MODEL_PATH

HIGH_RISK_CUTOFF = 0.60


class Predictor:
    def __init__(self, path=MODEL_PATH):
        bundle = joblib.load(path)
        self.pipeline = bundle["pipeline"]
        self.threshold = bundle["threshold"]
        self.version = bundle["version"]
        self.prep = self.pipeline.named_steps["prep"]
        self.booster = self.pipeline.named_steps["model"].get_booster()
        # map transformed columns back to source features, e.g. cat__family_income_Low -> family_income
        self.columns = []
        for name in self.prep.get_feature_names_out():
            base = name.split("__", 1)[1]
            for cat in MODEL_CATEGORICAL:
                if base.startswith(cat + "_"):
                    base = cat
            self.columns.append(base)

    def level(self, p: float) -> str:
        if p >= HIGH_RISK_CUTOFF:
            return "High"
        if p >= self.threshold:
            return "Medium"
        return "Low"

    def predict(self, rows: list[dict]) -> list[dict]:
        raw = pd.DataFrame(rows)
        features = build_features(raw)
        # SMOTE is skipped automatically at predict time
        proba = self.pipeline.predict_proba(features)[:, 1]

        transformed = self.prep.transform(features)
        contribs = self.booster.predict(xgb.DMatrix(np.asarray(transformed, dtype=float)), pred_contribs=True)

        results = []
        for i, p in enumerate(proba):
            impact: dict[str, float] = {}
            for col, value in zip(self.columns, contribs[i][:-1]):  # last column is the bias
                impact[col] = impact.get(col, 0.0) + float(value)
            factors = [
                {
                    "feature": f,
                    "label": FEATURE_LABELS[f],
                    "value": features.iloc[i][f].item() if hasattr(features.iloc[i][f], "item") else features.iloc[i][f],
                    "impact": round(v, 4),
                }
                for f, v in sorted(impact.items(), key=lambda kv: -abs(kv[1]))
            ]
            results.append({
                "risk_probability": round(float(p), 4),
                "risk_level": self.level(float(p)),
                "factors": factors,
                "model_version": self.version,
            })
        return results

    def predict_one(self, row: dict) -> dict:
        return self.predict([row])[0]


@lru_cache
def get_predictor() -> Predictor:
    return Predictor()
