from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from backend.ml.feature_engineering import extract_features, set_label_encoders
from backend.models.enums import Priority
from backend.models.schemas import TriageResult


REASON_CODE_BY_FEATURE = {
    "prior_retry_count": "RC01",
    "customer_failed_transactions": "RC01",
    "customer_failure_rate": "RC01",
    "hour_of_day": "RC01",
    "day_of_week": "RC01",
    "is_peak_hours": "RC01",
    "gateway_health_score": "RC02",
    "gateway_is_degraded": "RC02",
    "failure_category": "RC02",
    "customer_total_transactions": "RC03",
    "customer_lifetime_value_log": "RC03",
    "customer_opted_out": "RC03",
    "amount_paise": "RC04",
    "amount_log": "RC04",
    "amount_bucket": "RC04",
    "payment_method": "RC05",
    "bank_encoded": "RC05",
    "error_reason_encoded": "RC05",
    "failure_source": "RC05",
}


class TriageScorer:
    def __init__(self) -> None:
        model_dir = Path(__file__).resolve().parents[2] / "models"
        required_files = {
            "model": model_dir / "recovery_model.joblib",
            "explainer": model_dir / "shap_explainer.joblib",
            "features": model_dir / "feature_names.json",
            "encoders": model_dir / "label_encoders.joblib",
        }
        missing = [str(path) for path in required_files.values() if not path.exists()]
        if missing:
            raise FileNotFoundError(
                "ML model artifacts are missing. Run `python -m backend.ml.train_model`. "
                f"Missing: {', '.join(missing)}"
            )

        self.model = joblib.load(required_files["model"])
        self.shap_explainer = joblib.load(required_files["explainer"])
        with required_files["features"].open(encoding="utf-8") as file:
            self.feature_names: list[str] = json.load(file)
        self.label_encoders = joblib.load(required_files["encoders"])
        set_label_encoders(self.label_encoders)

    def score(
        self, event: dict[str, Any], gateway_health: dict[str, Any] | None = None
    ) -> TriageResult:
        features = extract_features(event, gateway_health)
        row = np.asarray([[features[name] for name in self.feature_names]], dtype=float)
        recovery_probability = float(self.model.predict_proba(row)[0, 1])
        amount_paise = max(0, int(event.get("amount_paise") or 0))
        expected_recovery_paise = int(round(recovery_probability * amount_paise))

        shap_values = self._get_shap_values(row)
        ranked_indices = np.argsort(np.abs(shap_values))[::-1][:3]
        top_importances = {
            self.feature_names[index]: round(float(shap_values[index]), 6)
            for index in ranked_indices
        }
        reason_codes = list(
            dict.fromkeys(REASON_CODE_BY_FEATURE[self.feature_names[index]] for index in ranked_indices)
        )

        return TriageResult(
            recovery_probability=recovery_probability,
            expected_recovery_paise=expected_recovery_paise,
            priority=self._priority(recovery_probability, amount_paise),
            shap_reason_codes=reason_codes,
            shap_feature_importances=top_importances,
            model_version="v1",
        )

    def _get_shap_values(self, row: np.ndarray) -> np.ndarray:
        raw_values = self.shap_explainer.shap_values(row)
        if isinstance(raw_values, list):
            raw_values = raw_values[-1]
        values = np.asarray(raw_values)
        if values.ndim == 3:
            values = values[:, :, -1]
        if values.ndim == 2:
            values = values[0]
        return values

    @staticmethod
    def _priority(probability: float, amount_paise: int) -> Priority:
        if probability > 0.7 and amount_paise > 1_000_000:
            return Priority.CRITICAL
        if probability > 0.5 and amount_paise > 100_000:
            return Priority.HIGH
        if probability > 0.3:
            return Priority.MEDIUM
        return Priority.LOW
