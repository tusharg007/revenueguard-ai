"""Recovery action execution and terminal audit nodes."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.agents.common import append_audit, customer_from_case, enum_value
from backend.agents.state import RecoveryState
from backend.guardrails.policy_engine import PolicyEngine
from backend.integrations import razorpay_client
from backend.models.enums import ActionType, RecoveryChannel
from backend.models.schemas import RecoveryAction


async def execute_action(state: RecoveryState) -> dict:
    PolicyEngine().assert_approved(state)

    case = state.get("case_data", {})
    strategy = state.get("strategy") or {}
    action_type = ActionType(enum_value(strategy.get("action_type", ActionType.STOP)))
    channel_value = strategy.get("channel") or state.get("selected_channel")
    channel = RecoveryChannel(enum_value(channel_value)) if channel_value else None
    output, status = await _execute(action_type, case, strategy, channel)
    action_id = str(uuid4())
    recovery_action = RecoveryAction(
        action_id=action_id,
        case_id=state.get("case_id", ""),
        action_type=action_type,
        channel=channel,
        status=status,
        input_state={"strategy": strategy},
        output_result=output,
        cost_paise=_channel_cost(channel),
        timestamp=datetime.now(timezone.utc),
        idempotency_key=_idempotency_key(state, action_type, channel),
    ).model_dump(mode="json")
    actions = [*state.get("actions", []), recovery_action]
    audit = append_audit(
        state,
        "execution",
        "execute_action",
        f"action={action_type.value}, channel={channel.value if channel else None}",
        f"action_id={action_id}, status={status}",
        "Action accepted by the deterministic execution adapter.",
    )
    audit[-1]["action_id"] = action_id
    return {"actions": actions, "audit_trail": audit}


async def _execute(
    action_type: ActionType,
    case: dict,
    strategy: dict,
    channel: RecoveryChannel | None,
) -> tuple[dict, str]:
    now = datetime.now(timezone.utc)
    delay = max(0, int(strategy.get("retry_delay_seconds", 0) or 0))

    if action_type == ActionType.PAYMENT_LINK:
        customer = customer_from_case(case)
        link = await asyncio.to_thread(
            razorpay_client.create_payment_link,
            int(case.get("amount_paise", 0) or 0),
            str(customer.get("name", "Customer")),
            str(customer.get("email", "unknown@example.com")),
            str(customer.get("phone", "+910000000000")),
            "RevenueGuard payment recovery",
            {"case_id": case.get("case_id", "")},
        )
        return {"payment_link": link}, "created"
    if action_type == ActionType.SMART_RETRY:
        return {"scheduled_for": (now + timedelta(seconds=delay)).isoformat()}, "scheduled"
    if action_type == ActionType.DEFER:
        return {"deferred_until": (now + timedelta(seconds=delay)).isoformat()}, "deferred"
    if action_type in {
        ActionType.NUDGE_EMAIL,
        ActionType.NUDGE_SMS,
        ActionType.NUDGE_WHATSAPP,
    }:
        return {
            "notification_logged": True,
            "channel": channel.value if channel else None,
            "message_content": strategy.get("message_content"),
        }, "queued"
    if action_type == ActionType.ESCALATE_HUMAN:
        return {"escalation_logged": True}, "escalated"
    return {"stop_logged": True}, "stopped"


def _idempotency_key(
    state: RecoveryState, action_type: ActionType, channel: RecoveryChannel | None
) -> str:
    case = state.get("case_data", {})
    retry_count = case.get("retry_count", case.get("prior_retry_count", 0))
    raw = f"{state.get('case_id')}:{action_type.value}:{channel}:{retry_count}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _channel_cost(channel: RecoveryChannel | None) -> int:
    return {
        RecoveryChannel.SMS: 25,
        RecoveryChannel.WHATSAPP: 50,
        RecoveryChannel.EMAIL: 0,
    }.get(channel, 0)


async def log_audit(state: RecoveryState) -> dict:
    strategy = state.get("strategy") or {}
    action = enum_value(strategy.get("action_type", ActionType.STOP))
    if state.get("approval_status") == "PENDING":
        final_decision = "approval_pending"
    elif state.get("error"):
        final_decision = "error"
    else:
        final_decision = action

    audit = append_audit(
        state,
        "recovery_graph",
        "log_audit",
        f"actions={len(state.get('actions', []))}",
        f"final_decision={final_decision}",
        "Recovery graph reached a terminal state.",
    )
    return {"audit_trail": audit, "final_decision": final_decision}
