"""Experiment assignment and control-arm nodes."""

from backend.agents.common import append_audit
from backend.agents.state import RecoveryState
from backend.config import get_settings
from backend.experiments.assignment import assign_experiment_arm
from backend.experiments.baseline import baseline_decide as decide_baseline


async def assign_experiment(state: RecoveryState) -> dict:
    arm = assign_experiment_arm(
        state["case_id"], variant_pct=get_settings().EXPERIMENT_VARIANT_PCT
    )
    audit = append_audit(
        state,
        "experiment_router",
        "assign_experiment",
        f"case_id={state['case_id']}",
        f"arm={arm.value}",
        "Stable MD5 bucket assignment.",
    )
    return {"experiment_arm": arm.value, "audit_trail": audit}


async def baseline_decide_node(state: RecoveryState) -> dict:
    case = state.get("case_data", {})
    retry_count = int(case.get("retry_count", case.get("prior_retry_count", 0)) or 0)
    decision = decide_baseline(case, retry_count=retry_count).model_dump(mode="json")
    audit = append_audit(
        state,
        "baseline",
        "baseline_decide",
        f"retry_count={retry_count}",
        f"action={decision['action_type']}",
        decision.get("reasoning", ""),
    )
    return {"strategy": decision, "audit_trail": audit}
