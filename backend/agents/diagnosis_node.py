"""LLM root-cause diagnosis node."""

from backend.agents.common import (
    append_audit,
    case_value,
    metadata_from_case,
    parse_json_response,
)
from backend.agents.llm_client import get_llm
from backend.agents.state import RecoveryState
from backend.models.schemas import DiagnosisResult


async def agent_diagnose(state: RecoveryState) -> dict:
    case = state.get("case_data", {})
    triage = state.get("triage") or {}
    health = state.get("gateway_health") or {}
    metadata = metadata_from_case(case)
    amount_paise = int(case.get("amount_paise", 0) or 0)

    prompt = f"""You are a payment failure diagnostic agent for Indian payment infrastructure.

CONTEXT (DO NOT modify these values; they come from deterministic systems):
- Recovery Probability: {triage.get('recovery_probability')} (from the ML model)
- SHAP Reason Codes: {triage.get('shap_reason_codes', [])}
- Gateway Health: {health.get('bank', 'unknown')} {health.get('rail', 'unknown')} - \
{health.get('state', 'unknown')} (success rate: {health.get('success_rate')}, \
baseline: {health.get('baseline_success_rate')})

PAYMENT FAILURE:
- Amount: INR {amount_paise / 100:.2f}
- Error Source: {case_value(case, 'error_source', 'source', 'failure_source')}, \
Step: {case_value(case, 'error_step', 'stage')}, \
Reason: {case_value(case, 'error_reason', 'reason', 'failure_reason')}
- Description: {case.get('error_description', '')}
- Payment Method: {metadata.get('payment_method', 'unknown')}, \
Bank: {metadata.get('bank_name', 'unknown')}

Analyze the root cause. Output ONLY valid JSON:
{{"root_cause": "...", "is_transient": true, \
"failure_category": "CUSTOMER_ACTION_NEEDED|SYSTEMIC_WAIT|PERMANENT_FAILURE", \
"reasoning": "...", "time_sensitivity": "immediate|hours|days"}}"""

    response = await get_llm().ainvoke(prompt)
    diagnosis = DiagnosisResult(**parse_json_response(response)).model_dump(mode="json")
    audit = append_audit(
        state,
        "diagnosis_agent",
        "agent_diagnose",
        "Deterministic ML and gateway context supplied as immutable inputs.",
        f"root_cause={diagnosis['root_cause']}, category={diagnosis['failure_category']}",
        diagnosis["reasoning"],
    )
    return {"diagnosis": diagnosis, "audit_trail": audit}
