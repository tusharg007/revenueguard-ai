from __future__ import annotations

import json
import math
import sys
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from backend.experiments.analyzer import ExperimentAnalyzer
from backend.experiments.assignment import assign_experiment_arm
from backend.experiments.baseline import baseline_decide
from backend.ml.triage_model import TriageScorer
from backend.models.enums import ActionType, ExperimentArm


@dataclass
class EvaluationRow:
    event_id: str
    arm: str
    amount_paise: int
    probability: float
    predicted_recoverable: bool
    actual_recoverable: bool
    action_type: str
    simulated_recovered: bool
    simulated_revenue_paise: int
    false_positive_cost_paise: int


class BatchEvaluator:
    """Offline evaluator for ML triage and simulated recovery decisions."""

    def __init__(self) -> None:
        self.scorer = TriageScorer()

    def run(
        self,
        batch_path: str = "data/test_batch.json",
        output_dir: str = "evals/results",
    ) -> dict[str, Any]:
        events = self._load_batch(batch_path)
        rows = [self._evaluate_event(event) for event in events]
        metrics = self._calculate_metrics(rows)
        report = {"metrics": metrics, "rows": [asdict(row) for row in rows]}
        self._save_outputs(report, output_dir)
        self._print_report(metrics, batch_path)
        return report

    def _evaluate_event(self, event: dict[str, Any]) -> EvaluationRow:
        normalized = self._normalize_event(event)
        health = self._simulate_gateway_health(normalized)
        triage = self.scorer.score(normalized, health)
        probability = triage.recovery_probability
        predicted_recoverable = probability >= 0.5
        actual_recoverable = bool(event.get("ground_truth", {}).get("is_recoverable", False))
        amount_paise = int(normalized.get("amount_paise") or 0)
        arm = assign_experiment_arm(str(normalized["case_id"]))

        if arm == ExperimentArm.CONTROL:
            decision = baseline_decide(normalized)
            action_type = decision.action_type.value
            simulated_recovered = self._simulate_baseline_recovery(event, actual_recoverable)
        else:
            action_type = self._agent_decide(normalized, health, probability)
            simulated_recovered = self._simulate_agent_recovery(
                event, action_type, probability, actual_recoverable
            )

        return EvaluationRow(
            event_id=str(event.get("event_id", normalized["case_id"])),
            arm=arm.value,
            amount_paise=amount_paise,
            probability=round(probability, 6),
            predicted_recoverable=predicted_recoverable,
            actual_recoverable=actual_recoverable,
            action_type=action_type,
            simulated_recovered=simulated_recovered,
            simulated_revenue_paise=amount_paise if simulated_recovered else 0,
            false_positive_cost_paise=self._false_positive_cost(action_type)
            if predicted_recoverable and not actual_recoverable
            else 0,
        )

    @staticmethod
    def _load_batch(batch_path: str) -> list[dict[str, Any]]:
        path = Path(batch_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Batch file not found: {batch_path}. Run `python -m data.generate_batch` first."
            )
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError("Evaluation batch must be a JSON list")
        return data

    @staticmethod
    def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
        return {
            "case_id": event.get("case_id") or event.get("event_id"),
            "event_type": event.get("event_type", "payment_failed"),
            "amount_paise": int(event.get("amount_paise") or 0),
            "currency": event.get("currency", "INR"),
            "error_source": event.get("error_source", "unknown"),
            "error_step": event.get("error_step", "payment_authorization"),
            "error_reason": event.get("error_reason", "unknown"),
            "error_code": event.get("error_code", "UNKNOWN_ERROR"),
            "error_description": event.get("error_description", ""),
            "customer": event.get("customer") or {},
            "merchant_id": event.get("merchant_id", "unknown"),
            "timestamp": event.get("timestamp"),
            "metadata": event.get("metadata") or {},
            "prior_retry_count": int((event.get("metadata") or {}).get("prior_retry_count", 0) or 0),
        }

    @staticmethod
    def _simulate_gateway_health(event: dict[str, Any]) -> dict[str, Any]:
        reason = str(event.get("error_reason", "")).lower()
        source = str(event.get("error_source", "")).lower()
        bank = str((event.get("metadata") or {}).get("bank_name") or "unknown")
        rail = str((event.get("metadata") or {}).get("payment_method") or "unknown")

        if reason in {"gateway_error", "server_error", "timeout"} or source in {
            "gateway",
            "network",
        }:
            success_rate = 0.68
            state = "open" if reason == "gateway_error" else "half_open"
        elif source == "business":
            success_rate = 0.96
            state = "closed"
        else:
            success_rate = 0.91
            state = "closed"

        return {
            "bank": bank,
            "rail": rail,
            "state": state,
            "success_rate": success_rate,
            "gateway_health_score": success_rate,
            "technical_failure_rate": max(0.0, 1.0 - success_rate),
            "sample_size": 75,
            "recommended_action": "DEFER" if state == "open" else "RETRY_NOW",
        }

    @staticmethod
    def _agent_decide(event: dict[str, Any], health: dict[str, Any], probability: float) -> str:
        customer = event.get("customer") or {}
        reason = str(event.get("error_reason", "")).lower()
        source = str(event.get("error_source", "")).lower()

        if customer.get("opted_out") or probability <= 0.15:
            return ActionType.STOP.value
        if source == "business":
            return ActionType.ESCALATE_HUMAN.value
        if health.get("state") == "open":
            return ActionType.DEFER.value
        if reason in {"gateway_error", "server_error", "timeout", "payment_failed"}:
            return ActionType.SMART_RETRY.value
        if reason in {"card_expired", "mandate_revoked"}:
            return ActionType.PAYMENT_LINK.value
        preferred_language = str(customer.get("preferred_language", "en")).lower()
        if preferred_language == "hi":
            return ActionType.NUDGE_WHATSAPP.value
        return ActionType.NUDGE_EMAIL.value

    @staticmethod
    def _simulate_baseline_recovery(event: dict[str, Any], actual_recoverable: bool) -> bool:
        if not actual_recoverable:
            return False
        reason = str(event.get("error_reason", "")).lower()
        return reason in {"gateway_error", "server_error", "timeout", "payment_failed"}

    @staticmethod
    def _simulate_agent_recovery(
        event: dict[str, Any],
        action_type: str,
        probability: float,
        actual_recoverable: bool,
    ) -> bool:
        if not actual_recoverable or action_type in {
            ActionType.STOP.value,
            ActionType.ESCALATE_HUMAN.value,
        }:
            return False
        method = str(event.get("ground_truth", {}).get("expected_recovery_method", "none")).lower()
        action_match = {
            "smart_retry": action_type in {ActionType.SMART_RETRY.value, ActionType.DEFER.value},
            "payment_link": action_type == ActionType.PAYMENT_LINK.value,
            "nudge": action_type
            in {
                ActionType.NUDGE_EMAIL.value,
                ActionType.NUDGE_SMS.value,
                ActionType.NUDGE_WHATSAPP.value,
            },
        }.get(method, False)
        return action_match and probability >= 0.35

    @staticmethod
    def _false_positive_cost(action_type: str) -> int:
        return {
            ActionType.NUDGE_SMS.value: 25,
            ActionType.NUDGE_WHATSAPP.value: 50,
            ActionType.NUDGE_EMAIL.value: 0,
            ActionType.PAYMENT_LINK.value: 100,
            ActionType.SMART_RETRY.value: 35,
            ActionType.DEFER.value: 10,
            ActionType.ESCALATE_HUMAN.value: 500,
        }.get(action_type, 0)

    def _calculate_metrics(self, rows: list[EvaluationRow]) -> dict[str, Any]:
        total_events = len(rows)
        revenue_at_risk = sum(row.amount_paise for row in rows)
        tp = sum(row.predicted_recoverable and row.actual_recoverable for row in rows)
        fp = sum(row.predicted_recoverable and not row.actual_recoverable for row in rows)
        fn = sum(not row.predicted_recoverable and row.actual_recoverable for row in rows)
        tn = sum(not row.predicted_recoverable and not row.actual_recoverable for row in rows)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        recovered = sum(row.simulated_revenue_paise for row in rows)
        false_positive_cost = sum(row.false_positive_cost_paise for row in rows)

        control_rows = [row for row in rows if row.arm == ExperimentArm.CONTROL.value]
        variant_rows = [row for row in rows if row.arm == ExperimentArm.TREATMENT.value]
        control_recovered = sum(row.simulated_recovered for row in control_rows)
        variant_recovered = sum(row.simulated_recovered for row in variant_rows)
        experiment = ExperimentAnalyzer().analyze(
            "recovery_agent_v1",
            int(control_recovered),
            len(control_rows),
            int(variant_recovered),
            len(variant_rows),
        )

        return {
            "total_events": total_events,
            "revenue_at_risk_paise": revenue_at_risk,
            "true_positives": int(tp),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_negatives": int(tn),
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "simulated_recovery_paise": recovered,
            "simulated_recovery_rate": recovered / revenue_at_risk if revenue_at_risk else 0.0,
            "false_positive_cost_paise": false_positive_cost,
            "experiment": experiment,
        }

    @staticmethod
    def _save_outputs(report: dict[str, Any], output_dir: str) -> None:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        with (path / "summary.json").open("w", encoding="utf-8") as file:
            json.dump(report["metrics"], file, indent=2)
        with (path / "rows.json").open("w", encoding="utf-8") as file:
            json.dump(report["rows"], file, indent=2)

    def _print_report(self, metrics: dict[str, Any], batch_path: str) -> None:
        experiment = metrics["experiment"]
        lift_pp = experiment["absolute_lift"] * 100
        recovered_rate = metrics["simulated_recovery_rate"] * 100
        print("═══════════════════════════════════════")
        print("REVENUEGUARD AI — BATCH EVALUATION")
        print("═══════════════════════════════════════")
        print(f"Dataset: {metrics['total_events']} events ({batch_path})")
        print(f"Revenue at Risk: {self._money(metrics['revenue_at_risk_paise'])}")
        print(
            "ML Precision: "
            f"{metrics['precision'] * 100:.1f}% | "
            f"Recall: {metrics['recall'] * 100:.1f}% | "
            f"F1: {metrics['f1'] * 100:.1f}%"
        )
        print(
            "Recovered (simulated): "
            f"{self._money(metrics['simulated_recovery_paise'])} ({recovered_rate:.1f}%)"
        )
        print(f"FP Cost: {self._money(metrics['false_positive_cost_paise'])}")
        print(
            "Baseline: "
            f"{experiment['control_rate'] * 100:.1f}% | "
            f"Agent: {experiment['variant_rate'] * 100:.1f}% | "
            f"Lift: {lift_pp:+.1f}pp | p={experiment['p_value']:.3f}"
        )
        print("═══════════════════════════════════════")

    @staticmethod
    def _money(paise: int) -> str:
        rupees = int(round(paise / 100))
        sign = "-" if rupees < 0 else ""
        digits = str(abs(rupees))
        if len(digits) <= 3:
            grouped = digits
        else:
            grouped = f"{digits[-3:]}"
            prefix = digits[:-3]
            groups = []
            while prefix:
                groups.append(prefix[-2:])
                prefix = prefix[:-2]
            grouped = f"{','.join(reversed(groups))},{grouped}"
        return f"{sign}₹{grouped}"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    warnings.filterwarnings(
        "ignore",
        message="LightGBM binary classifier with TreeExplainer shap values output has changed.*",
    )
    BatchEvaluator().run()


if __name__ == "__main__":
    main()
