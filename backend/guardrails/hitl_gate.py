"""Human-in-the-loop approval request node."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx

from backend.agents.common import append_audit, case_value, enum_value
from backend.agents.state import RecoveryState
from backend.config import get_settings
from backend.models.enums import ActionType
from backend.models.schemas import ApprovalRecord


async def request_approval_node(state: RecoveryState) -> dict:
    case = state.get("case_data", {})
    strategy = state.get("strategy") or {}
    now = datetime.now(timezone.utc)
    action = ActionType(enum_value(strategy.get("action_type", ActionType.STOP)))
    record = ApprovalRecord(
        approval_id=f"APR-{uuid4().hex[:12].upper()}",
        case_id=state.get("case_id", ""),
        payment_id=str(
            case_value(case, "external_payment_id", "razorpay_payment_id", default="unknown")
        ),
        amount_paise=int(case.get("amount_paise", 0) or 0),
        requested_action=action,
        agent_recommendation=str(strategy.get("reasoning", "")),
        status="PENDING",
        requested_at=now,
        expires_at=now + timedelta(hours=2),
    )
    approval = record.model_dump(mode="json")
    delivery_note = "Approval recorded for API persistence."

    webhook_url = get_settings().N8N_APPROVAL_WEBHOOK_URL
    if webhook_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=approval)
                response.raise_for_status()
            delivery_note = "Approval sent to n8n."
        except httpx.HTTPError as exc:
            delivery_note = f"Approval created; n8n delivery failed ({type(exc).__name__})."

    audit = append_audit(
        state,
        "hitl_gate",
        "request_approval",
        f"action={action.value}, amount_paise={record.amount_paise}",
        f"approval_id={record.approval_id}, status=PENDING",
        delivery_note,
        guardrails=["high_value_approval"],
    )
    return {
        "approval_status": "PENDING",
        "approval_record": approval,
        "audit_trail": audit,
    }
