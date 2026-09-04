"""Redis queue worker for RevenueGuard recovery cases."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import redis.asyncio as redis
from sqlalchemy import select

from backend.agents.graph import build_recovery_graph
from backend.api.events import publish_event
from backend.config import get_settings
from backend.db import database
from backend.db.orm_models import (
    AuditLog,
    ExperimentAssignmentRecord,
    GatewayHealthRecord,
    RecoveryActionRecord,
    RecoveryApproval,
    RecoveryCase,
)
from backend.models.enums import EventStatus


logger = logging.getLogger(__name__)
_graph = None


async def process_case(case_id: str, redis_client: Any | None = None) -> None:
    """Run one case through the graph and persist every resulting record."""
    if database.async_session_maker is None:
        database.init_engine()
    if database.async_session_maker is None:
        raise RuntimeError("Database session factory is unavailable")

    async with database.async_session_maker() as db:
        case = await db.scalar(select(RecoveryCase).where(RecoveryCase.case_id == case_id))
        if case is None:
            logger.warning("Skipping missing recovery case %s", case_id)
            return

        try:
            case.status = EventStatus.TRIAGING.value
            approval = await _active_approval(case_id, db)
            state = _build_state(case, approval)
            result = await _get_graph().ainvoke(state)
            await _persist_result(case, result, db)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            await _record_failure(case_id, exc, db)
            await db.commit()
            logger.exception("Failed processing case %s", case_id)
            await publish_event(
                redis_client,
                {"type": "case_failed", "case_id": case_id, "error": str(exc)},
            )
            return

    await publish_event(
        redis_client,
        {
            "type": "case_processed",
            "case_id": case_id,
            "status": result.get("final_decision"),
            "experiment_arm": result.get("experiment_arm"),
        },
    )
    print(f"Processed {case_id}: {result.get('final_decision')}")


async def worker_loop() -> None:
    """Block on Redis BRPOP and process recovery jobs one at a time."""
    database.init_engine()
    client = redis.from_url(
        get_settings().REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=1.0,
        socket_timeout=5.0,
    )
    try:
        await client.ping()
        print("RevenueGuard worker listening on recovery_queue")
        while True:
            item = await client.brpop("recovery_queue", timeout=5)
            if item is None:
                continue
            _, case_id = item
            await process_case(str(case_id), client)
    finally:
        await client.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(worker_loop())


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_recovery_graph()
    return _graph


def _build_state(case: RecoveryCase, approval: RecoveryApproval | None) -> dict:
    stored_customer = dict(case.customer_data or {})
    context = stored_customer.pop("_revenueguard_context", {})
    return {
        "case_id": case.case_id,
        "case_data": {
            "case_id": case.case_id,
            "event_type": case.event_type,
            "external_payment_id": case.external_payment_id,
            "external_order_id": case.external_order_id,
            "amount_paise": case.amount_paise,
            "currency": case.currency,
            "category": case.failure_category,
            "source": case.failure_source,
            "reason": case.failure_reason,
            "error_code": case.error_code,
            "error_description": context.get("error_description", ""),
            "customer": stored_customer,
            "merchant_id": case.merchant_id,
            "metadata": context.get("metadata", {}),
            "timestamp": case.created_at,
            "retry_count": case.retry_count,
            "last_retry_at": case.last_retry_at,
        },
        "actions": [],
        "audit_trail": [],
        "needs_approval": False,
        "approval_status": approval.status if approval else None,
        "approval_record": _approval_state(approval),
    }


async def _active_approval(case_id: str, db) -> RecoveryApproval | None:
    return await db.scalar(
        select(RecoveryApproval)
        .where(RecoveryApproval.case_id == case_id)
        .where(RecoveryApproval.status == "APPROVED")
        .order_by(RecoveryApproval.approved_at.desc())
        .limit(1)
    )


async def _persist_result(case: RecoveryCase, result: dict, db) -> None:
    triage = result.get("triage") or {}
    health = result.get("gateway_health") or {}
    strategy = result.get("strategy") or {}
    case.recovery_probability = triage.get("recovery_probability")
    case.shap_reason_codes = triage.get("shap_reason_codes") or []
    case.experiment_arm = result.get("experiment_arm")
    case.gateway_health_state = health.get("state")
    case.status = _case_status(result, strategy)
    case.updated_at = datetime.now(timezone.utc)

    if strategy.get("action_type") == "smart_retry":
        case.retry_count += 1
        case.last_retry_at = datetime.now(timezone.utc)

    if health:
        db.add(
            GatewayHealthRecord(
                bank=str(health.get("bank", "unknown")),
                rail=str(health.get("rail", "unknown")),
                state=str(health.get("state", "closed")),
                success_rate=float(health.get("success_rate", 0.0) or 0.0),
                technical_failure_rate=float(health.get("technical_failure_rate", 0.0) or 0.0),
                sample_size=int(health.get("sample_size", 0) or 0),
                snapshot_data={"case_id": case.case_id, **health},
            )
        )

    if case.experiment_arm:
        existing_assignment = await db.scalar(
            select(ExperimentAssignmentRecord).where(
                ExperimentAssignmentRecord.case_id == case.case_id,
                ExperimentAssignmentRecord.experiment_id == "recovery_agent_v1",
            )
        )
        if existing_assignment is None:
            db.add(
                ExperimentAssignmentRecord(
                    experiment_id="recovery_agent_v1",
                    case_id=case.case_id,
                    arm=case.experiment_arm,
                )
            )

    for action in result.get("actions", []):
        existing = await db.scalar(
            select(RecoveryActionRecord).where(
                RecoveryActionRecord.idempotency_key == action["idempotency_key"]
            )
        )
        if existing is None:
            db.add(
                RecoveryActionRecord(
                    id=action["action_id"],
                    case_id=case.case_id,
                    action_type=action["action_type"],
                    channel=action.get("channel"),
                    status=action.get("status", "pending"),
                    input_state=action.get("input_state", {}),
                    output_result=action.get("output_result", {}),
                    cost_paise=int(action.get("cost_paise", 0) or 0),
                    idempotency_key=action["idempotency_key"],
                )
            )

    for audit in result.get("audit_trail", []):
        db.add(
            AuditLog(
                id=audit.get("id", str(uuid4())),
                case_id=case.case_id,
                action_id=audit.get("action_id"),
                agent_name=audit.get("agent_name", "recovery_graph"),
                step=audit.get("step", "unknown"),
                input_summary=audit.get("input_summary", ""),
                output_summary=audit.get("output_summary", ""),
                reasoning=audit.get("reasoning", ""),
                guardrails_applied=audit.get("guardrails_applied", []),
                duration_ms=int(audit.get("duration_ms", 0) or 0),
            )
        )

    approval_data = result.get("approval_record")
    if approval_data and result.get("approval_status") == "PENDING":
        existing_approval = await db.scalar(
            select(RecoveryApproval).where(
                RecoveryApproval.approval_id == approval_data["approval_id"]
            )
        )
        if existing_approval is None:
            db.add(
                RecoveryApproval(
                    approval_id=approval_data["approval_id"],
                    case_id=case.case_id,
                    payment_id=approval_data["payment_id"],
                    amount_paise=int(approval_data["amount_paise"]),
                    requested_action=approval_data["requested_action"],
                    agent_recommendation=approval_data.get("agent_recommendation", ""),
                    status="PENDING",
                    requested_at=_parse_datetime(approval_data["requested_at"]),
                    expires_at=_parse_datetime(approval_data["expires_at"]),
                )
            )


async def _record_failure(case_id: str, exc: Exception, db) -> None:
    case = await db.scalar(select(RecoveryCase).where(RecoveryCase.case_id == case_id))
    if case is not None:
        case.status = EventStatus.FAILED.value
        case.updated_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            id=str(uuid4()),
            case_id=case_id,
            agent_name="worker",
            step="process_case",
            input_summary="Recovery graph invocation",
            output_summary="failed",
            reasoning=str(exc),
            guardrails_applied=[],
            duration_ms=0,
        )
    )


def _case_status(result: dict, strategy: dict) -> str:
    if result.get("approval_status") == "PENDING":
        return EventStatus.ESCALATED.value
    action = str(strategy.get("action_type", "")).lower()
    if action == "stop":
        return EventStatus.STOPPED.value
    if action == "escalate_human":
        return EventStatus.ESCALATED.value
    return EventStatus.EXECUTING.value


def _approval_state(approval: RecoveryApproval | None) -> dict | None:
    if approval is None:
        return None
    return {"approval_id": approval.approval_id, "expires_at": approval.expires_at.isoformat()}


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


if __name__ == "__main__":
    main()
