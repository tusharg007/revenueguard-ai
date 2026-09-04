from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from sklearn.preprocessing import LabelEncoder


FEATURE_NAMES = [
    "amount_paise",
    "amount_log",
    "amount_bucket",
    "failure_category",
    "failure_source",
    "payment_method",
    "bank_encoded",
    "error_reason_encoded",
    "hour_of_day",
    "day_of_week",
    "is_peak_hours",
    "customer_lifetime_value_log",
    "customer_total_transactions",
    "customer_failed_transactions",
    "customer_failure_rate",
    "customer_opted_out",
    "gateway_health_score",
    "gateway_is_degraded",
    "prior_retry_count",
]

FAILURE_CATEGORY_ENCODING = {
    "customer": 0,
    "systemic": 1,
    "business": 2,
    "unknown": 3,
}
FAILURE_SOURCE_ENCODING = {
    "customer": 0,
    "bank": 1,
    "gateway": 2,
    "network": 3,
    "business": 4,
}
PAYMENT_METHOD_ENCODING = {
    "upi": 0,
    "card": 1,
    "netbanking": 2,
    "wallet": 3,
}
UNKNOWN_LABEL = "__unknown__"

_label_encoders: dict[str, LabelEncoder] = {}


def get_feature_names() -> list[str]:
    return FEATURE_NAMES.copy()


def fit_label_encoders(events: list[dict[str, Any]]) -> dict[str, LabelEncoder]:
    """Fit serving-safe encoders using only the supplied training events."""
    banks = [str(_metadata(event).get("bank_name") or UNKNOWN_LABEL) for event in events]
    reasons = [str(event.get("error_reason") or event.get("reason") or UNKNOWN_LABEL) for event in events]

    encoders = {
        "bank": LabelEncoder().fit([*banks, UNKNOWN_LABEL]),
        "error_reason": LabelEncoder().fit([*reasons, UNKNOWN_LABEL]),
    }
    set_label_encoders(encoders)
    return encoders


def get_label_encoders() -> dict[str, LabelEncoder]:
    return _label_encoders.copy()


def set_label_encoders(encoders: dict[str, LabelEncoder]) -> None:
    required = {"bank", "error_reason"}
    missing = required.difference(encoders)
    if missing:
        raise ValueError(f"Missing label encoders: {', '.join(sorted(missing))}")

    _label_encoders.clear()
    _label_encoders.update(encoders)


def extract_features(
    event: dict[str, Any], gateway_health: dict[str, Any] | None = None
) -> dict[str, float | int]:
    customer = event.get("customer") or {}
    metadata = _metadata(event)
    amount_paise = max(0, int(event.get("amount_paise") or 0))
    source = _enum_value(event.get("error_source") or event.get("source") or "unknown")
    reason = str(event.get("error_reason") or event.get("reason") or UNKNOWN_LABEL).lower()
    category = _enum_value(event.get("failure_category") or event.get("category") or "")
    if not category:
        category = _infer_failure_category(source, reason)

    timestamp = _parse_timestamp(event.get("timestamp"))
    hour = timestamp.hour
    total_transactions = max(0, int(customer.get("total_transactions") or 0))
    failed_transactions = max(0, int(customer.get("failed_transactions") or 0))
    failure_rate = failed_transactions / total_transactions if total_transactions else 0.0

    health = gateway_health or {}
    health_score = float(
        health.get(
            "gateway_health_score",
            health.get("health_score", health.get("success_rate", 0.95)),
        )
    )
    health_score = min(1.0, max(0.0, health_score))
    health_state = _enum_value(health.get("state") or "closed")
    degraded = health.get("gateway_is_degraded", health.get("is_degraded"))
    if degraded is None:
        degraded = health_state in {"open", "half_open", "degraded", "down"} or health_score < 0.90

    prior_retry_count = event.get("prior_retry_count")
    if prior_retry_count is None:
        prior_retry_count = metadata.get("prior_retry_count", metadata.get("retry_count", 0))

    features: dict[str, float | int] = {
        "amount_paise": amount_paise,
        "amount_log": math.log10(max(amount_paise, 1)),
        "amount_bucket": _amount_bucket(amount_paise),
        "failure_category": FAILURE_CATEGORY_ENCODING.get(category, 3),
        "failure_source": FAILURE_SOURCE_ENCODING.get(source, 4),
        "payment_method": PAYMENT_METHOD_ENCODING.get(
            str(metadata.get("payment_method") or "").lower(), 3
        ),
        "bank_encoded": _encode_label("bank", metadata.get("bank_name")),
        "error_reason_encoded": _encode_label("error_reason", reason),
        "hour_of_day": hour,
        "day_of_week": timestamp.weekday(),
        "is_peak_hours": int(10 <= hour < 14 or 19 <= hour < 23),
        "customer_lifetime_value_log": math.log10(
            max(int(customer.get("lifetime_value_paise") or 0), 1)
        ),
        "customer_total_transactions": total_transactions,
        "customer_failed_transactions": failed_transactions,
        "customer_failure_rate": min(1.0, failure_rate),
        "customer_opted_out": int(bool(customer.get("opted_out", False))),
        "gateway_health_score": health_score,
        "gateway_is_degraded": int(bool(degraded)),
        "prior_retry_count": max(0, int(prior_retry_count or 0)),
    }
    return {name: features[name] for name in FEATURE_NAMES}


def _metadata(event: dict[str, Any]) -> dict[str, Any]:
    metadata = event.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _enum_value(value: Any) -> str:
    raw_value = getattr(value, "value", value)
    return str(raw_value).lower()


def _infer_failure_category(source: str, reason: str) -> str:
    if source == "business":
        return "business"
    if source in {"gateway", "network"}:
        return "systemic"
    if source == "customer":
        return "customer"
    if source == "bank":
        if reason in {"payment_failed", "gateway_error", "server_error", "timeout"}:
            return "systemic"
        if reason in {
            "insufficient_funds",
            "incorrect_pin",
            "wrong_pin",
            "card_expired",
            "authentication_failed",
        }:
            return "customer"
    return "unknown"


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now()


def _amount_bucket(amount_paise: int) -> int:
    boundaries = (20_000, 50_000, 100_000, 500_000, 1_000_000)
    return sum(amount_paise > boundary for boundary in boundaries)


def _encode_label(name: str, value: Any) -> int:
    encoder = _label_encoders.get(name)
    if encoder is None:
        raise RuntimeError(
            "Label encoders are not initialized. Call fit_label_encoders() during training "
            "or set_label_encoders() before scoring."
        )

    label = str(value or UNKNOWN_LABEL)
    known_labels = set(encoder.classes_)
    if label not in known_labels:
        label = UNKNOWN_LABEL
    return int(encoder.transform([label])[0])
