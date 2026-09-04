"""Deterministic ML enrichment node."""

from backend.agents.common import append_audit
from backend.agents.state import RecoveryState
from backend.ml.triage_model import TriageScorer


_scorer: TriageScorer | None = None


def _get_scorer() -> TriageScorer:
    global _scorer
    if _scorer is None:
        _scorer = TriageScorer()
    return _scorer


async def enrich_with_ml(state: RecoveryState) -> dict:
    result = _get_scorer().score(state.get("case_data", {}), state.get("gateway_health"))
    triage = result.model_dump(mode="json")
    audit = append_audit(
        state,
        "triage_model",
        "enrich_ml",
        f"case_id={state.get('case_id', '')}",
        f"probability={triage['recovery_probability']:.6f}, priority={triage['priority']}",
        "Recovery probability produced by the deterministic ML model.",
    )
    return {"triage": triage, "audit_trail": audit}
