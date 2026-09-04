"""Recovery strategy node with deterministic safety overrides."""

from backend.agents.common import append_audit, case_value, customer_from_case, parse_json_response
from backend.agents.llm_client import get_llm
from backend.agents.state import RecoveryState
from backend.config import get_settings
from backend.models.enums import ActionType
from backend.models.schemas import StrategyDecision


async def agent_strategize(state: RecoveryState) -> dict:
    override = _deterministic_override(state)
    if override is not None:
        return _strategy_result(state, override, "Deterministic override applied.")

    triage = state.get("triage") or {}
    health = state.get("gateway_health") or {}
    diagnosis = state.get("diagnosis") or {}
    case = state.get("case_data", {})
    prompt = f"""You are a recovery strategy agent for Indian payments.

IMMUTABLE DETERMINISTIC CONTEXT (never recalculate or return the probability):
- Recovery probability: {triage.get('recovery_probability')}
- Priority: {triage.get('priority')}
- Gateway state: {health.get('state')} (recommended action: {health.get('recommended_action')})
- Retry count: {case.get('retry_count', case.get('prior_retry_count', 0))}

DIAGNOSIS:
{diagnosis}

Choose exactly one action from SMART_RETRY, PAYMENT_LINK, NUDGE_EMAIL, NUDGE_SMS,
NUDGE_WHATSAPP, DEFER, ESCALATE_HUMAN, STOP. Draft customer-facing text only when
the action needs a message.

Output ONLY valid JSON:
{{"action_type": "SMART_RETRY", "reasoning": "...", \
"retry_delay_seconds": 0, "message_content": null}}"""

    payload = _normalize_strategy_payload(
        parse_json_response(await get_llm().ainvoke(prompt))
    )
    decision = StrategyDecision(**payload)
    return _strategy_result(state, decision, "LLM selected an action within the fixed action set.")


def _normalize_strategy_payload(payload: dict) -> dict:
    payload = dict(payload)
    payload.pop("recovery_probability", None)
    payload["action_type"] = str(payload.get("action_type", "stop")).lower()
    payload["retry_delay_seconds"] = max(
        0, int(payload.get("retry_delay_seconds") or 0)
    )
    return payload


def _deterministic_override(state: RecoveryState) -> StrategyDecision | None:
    case = state.get("case_data", {})
    health = state.get("gateway_health") or {}
    customer = customer_from_case(case)
    retry_count = int(case.get("retry_count", case.get("prior_retry_count", 0)) or 0)
    category = str(case_value(case, "failure_category", "category", default="")).lower()

    if str(health.get("state", "")).lower() == "open":
        return StrategyDecision(
            action_type=ActionType.DEFER,
            retry_delay_seconds=int(health.get("retry_after_seconds", 600) or 600),
            reasoning="Gateway circuit breaker is open.",
        )
    if customer.get("opted_out", False):
        return StrategyDecision(
            action_type=ActionType.STOP,
            reasoning="Customer has opted out of recovery contact.",
            stopping_reason="Customer opted out",
        )
    if retry_count >= get_settings().MAX_RETRY_ATTEMPTS:
        return StrategyDecision(
            action_type=ActionType.STOP,
            reasoning="Maximum retry count reached.",
            stopping_reason="Retry limit reached",
        )
    if category == "business":
        return StrategyDecision(
            action_type=ActionType.ESCALATE_HUMAN,
            reasoning="Business failures require merchant review.",
            escalation_reason="Business-rule failure",
        )
    return None


def _strategy_result(
    state: RecoveryState, decision: StrategyDecision, audit_reason: str
) -> dict:
    strategy = decision.model_dump(mode="json")
    audit = append_audit(
        state,
        "strategy_agent",
        "agent_strategize",
        f"diagnosis={state.get('diagnosis')}",
        f"action={strategy['action_type']}",
        f"{audit_reason} {strategy.get('reasoning', '')}".strip(),
    )
    return {"strategy": strategy, "audit_trail": audit}
