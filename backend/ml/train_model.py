from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import shap
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, log_loss, precision_score, recall_score, roc_auc_score
from xgboost import XGBClassifier

from backend.ml.feature_engineering import (
    extract_features,
    fit_label_encoders,
    get_feature_names,
)
from data.generator import SyntheticDataGenerator


MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
RANDOM_STATE = 42


def _feature_matrix(events: list[dict[str, Any]], feature_names: list[str]) -> np.ndarray:
    rows = [extract_features(event) for event in events]
    return np.asarray([[row[name] for name in feature_names] for row in rows], dtype=float)


def _metrics(model: Any, features: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    probabilities = model.predict_proba(features)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    return {
        "auc_roc": roc_auc_score(labels, probabilities),
        "log_loss": log_loss(labels, probabilities),
        "precision": precision_score(labels, predictions, zero_division=0),
        "recall": recall_score(labels, predictions, zero_division=0),
        "f1": f1_score(labels, predictions, zero_division=0),
    }


def _print_comparison(results: dict[str, dict[str, float]]) -> None:
    print("\nModel comparison")
    print(f"{'Model':<24} {'AUC-ROC':>9} {'Log-loss':>9} {'Precision':>10} {'Recall':>8} {'F1':>8}")
    print("-" * 74)
    for name, scores in results.items():
        print(
            f"{name:<24} {scores['auc_roc']:>9.4f} {scores['log_loss']:>9.4f} "
            f"{scores['precision']:>10.4f} {scores['recall']:>8.4f} {scores['f1']:>8.4f}"
        )


def _shap_values(explainer: Any, row: np.ndarray) -> np.ndarray:
    raw_values = explainer.shap_values(row)
    if isinstance(raw_values, list):
        raw_values = raw_values[-1]
    values = np.asarray(raw_values)
    if values.ndim == 3:
        values = values[:, :, -1]
    if values.ndim == 2:
        values = values[0]
    return values


def main() -> None:
    generator = SyntheticDataGenerator(num_events=2000)
    train_events, test_events = generator.generate_for_training()
    feature_names = get_feature_names()
    label_encoders = fit_label_encoders(train_events)

    x_train = _feature_matrix(train_events, feature_names)
    x_test = _feature_matrix(test_events, feature_names)
    y_train = np.asarray(
        [int(event["ground_truth"]["is_recoverable"]) for event in train_events]
    )
    y_test = np.asarray([int(event["ground_truth"]["is_recoverable"]) for event in test_events])
    positives = int(y_train.sum())
    negatives = len(y_train) - positives
    scale_pos_weight = negatives / positives if positives else 1.0

    models = {
        "LightGBM": LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            class_weight="balanced",
            verbose=-1,
            random_state=RANDOM_STATE,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "Calibrated LogisticRegression": CalibratedClassifierCV(
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=RANDOM_STATE,
            ),
            cv=5,
        ),
    }

    results: dict[str, dict[str, float]] = {}
    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(x_train, y_train)
        results[name] = _metrics(model, x_test, y_test)

    _print_comparison(results)
    champion_name = max(results, key=lambda name: results[name]["auc_roc"])
    champion = models[champion_name]
    print(f"\nChampion: {champion_name} (AUC-ROC {results[champion_name]['auc_roc']:.4f})")

    try:
        explainer = shap.TreeExplainer(champion)
    except Exception as exc:
        tree_names = ("LightGBM", "XGBoost")
        champion_name = max(tree_names, key=lambda name: results[name]["auc_roc"])
        champion = models[champion_name]
        explainer = shap.TreeExplainer(champion)
        print(
            "Highest-AUC model was not TreeExplainer-compatible; "
            f"using {champion_name} as the explainable deployment champion ({exc})."
        )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(champion, MODEL_DIR / "recovery_model.joblib")
    joblib.dump(explainer, MODEL_DIR / "shap_explainer.joblib")
    joblib.dump(label_encoders, MODEL_DIR / "label_encoders.joblib")
    with (MODEL_DIR / "feature_names.json").open("w", encoding="utf-8") as file:
        json.dump(feature_names, file, indent=2)

    print("\nExample SHAP analyses")
    for index in range(3):
        values = _shap_values(explainer, x_test[index : index + 1])
        ranked = np.argsort(np.abs(values))[::-1][:3]
        reasons = ", ".join(f"{feature_names[i]}={values[i]:+.4f}" for i in ranked)
        probability = champion.predict_proba(x_test[index : index + 1])[0, 1]
        print(f"  Event {index + 1}: P(recovery)={probability:.3f}; {reasons}")

    print(f"\nSaved model artifacts to {MODEL_DIR}")


if __name__ == "__main__":
    main()
