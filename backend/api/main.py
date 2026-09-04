"""FastAPI application for RevenueGuard AI."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.events import ConnectionManager, publish_event, relay_redis_events
from backend.config import get_settings
from backend.db import database
from backend.db.database import Base, get_db
from backend.db.orm_models import (
    AuditLog,
    Experiment,
    GatewayHealthRecord,
    RecoveryActionRecord,
    RecoveryApproval,
    RecoveryCase,
)
from backend.experiments.analyzer import ExperimentAnalyzer
from backend.gateway_health.aggregator import GatewayHealthAggregator
from backend.gateway_health.circuit_breaker import GatewayCircuitBreaker
from backend.gateway_health.downtime_monitor import DowntimeMonitor
from backend.integrations.normalizer import _classify_failure
from backend.models.enums import EventStatus
from backend.redis_client import create_redis_client
from backend.webhooks.checkout_api import router as checkout_router
from backend.webhooks.razorpay_handler import router as razorpay_router
from data.generator import SyntheticDataGenerator


connections = ConnectionManager()


class ApprovalRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=255)


class BatchSimulationRequest(BaseModel):
    count: int = Field(default=50, ge=1, le=2_000)


class OutageSimulationRequest(BaseModel):
    bank: str = Field(default="SBI", min_length=1, max_length=50)
    rail: str = Field(default="UPI", min_length=1, max_length=50)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_engine()
    if database.engine is None or database.async_session_maker is None:
        raise RuntimeError("Database engine initialization failed")

    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with database.async_session_maker() as session:
        await _create_default_experiment(session)
        await session.commit()

    app.state.redis = None
    app.state.event_listener = None
    candidate = create_redis_client(
        get_settings().REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=0.25,
        socket_timeout=0.5,
    )
    try:
        await candidate.ping()
    except Exception:
        await candidate.aclose()
    else:
        app.state.redis = candidate
        app.state.event_listener = asyncio.create_task(relay_redis_events(candidate, connections))

    try:
        yield
    finally:
        listener = app.state.event_listener
        if listener is not None:
            listener.cancel()
            with suppress(asyncio.CancelledError):
                await listener
        if app.state.redis is not None:
            await app.state.redis.aclose()
        if database.engine is not None:
            await database.engine.dispose()


app = FastAPI(title="RevenueGuard AI", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(razorpay_router)
app.include_router(checkout_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "environment": get_settings().APP_ENV}


@app.get("/api/cases")
async def list_cases(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    experiment_arm: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    filters = []
    if status:
        filters.append(RecoveryCase.status == status)
    if experiment_arm:
        filters.append(RecoveryCase.experiment_arm == experiment_arm)

    total_query = select(func.count()).select_from(RecoveryCase).where(*filters)
    total = int((await db.scalar(total_query)) or 0)
    query = (
        select(RecoveryCase)
        .where(*filters)
        .order_by(RecoveryCase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    cases = (await db.execute(query)).scalars().all()
    return {
        "items": [_case_summary(case) for case in cases],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    case = await _get_case_or_404(case_id, db)
    actions = (
        await db.execute(
            select(RecoveryActionRecord)
            .where(RecoveryActionRecord.case_id == case_id)
            .order_by(RecoveryActionRecord.created_at.asc())
        )
    ).scalars().all()
    audits = (
        await db.execute(
            select(AuditLog).where(AuditLog.case_id == case_id).order_by(AuditLog.created_at.asc())
        )
    ).scalars().all()
    approvals = (
        await db.execute(
            select(RecoveryApproval)
            .where(RecoveryApproval.case_id == case_id)
            .order_by(RecoveryApproval.requested_at.desc())
        )
    ).scalars().all()
    health = await _case_gateway_health(case_id, db)
    timeline = _timeline(case, actions, audits)
    return {
        "case": _case_detail(case),
        "triage": {
            "recovery_probability": case.recovery_probability,
            "shap_reason_codes": case.shap_reason_codes or [],
        },
        "gateway_health": health,
        "actions": [_action_dict(action) for action in actions],
        "audit_trail": [_audit_dict(audit) for audit in audits],
        "approvals": [_approval_dict(approval) for approval in approvals],
        "timeline": timeline,
    }


@app.get("/api/metrics")
async def metrics(db: AsyncSession = Depends(get_db)) -> dict:
    total_events = int((await db.scalar(select(func.count()).select_from(RecoveryCase))) or 0)
    revenue_at_risk_query = select(func.coalesce(func.sum(RecoveryCase.amount_paise), 0))
    revenue_at_risk = int((await db.scalar(revenue_at_risk_query)) or 0)
    revenue_recovered = int(
        (
            await db.scalar(
                select(func.coalesce(func.sum(RecoveryCase.recovered_amount_paise), 0))
            )
        )
        or 0
    )
    recovered_cases = int(
        (
            await db.scalar(
                select(func.count()).select_from(RecoveryCase).where(
                    RecoveryCase.status == EventStatus.RECOVERED.value
                )
            )
        )
        or 0
    )
    grouped = await db.execute(
        select(
            RecoveryCase.experiment_arm,
            func.count(),
            func.coalesce(
                func.sum(case((RecoveryCase.status == EventStatus.RECOVERED.value, 1), else_=0)),
                0,
            ),
        ).group_by(RecoveryCase.experiment_arm)
    )
    by_arm = {
        arm or "unassigned": {
            "total": int(total or 0),
            "recovered": int(recovered or 0),
            "recovery_rate": (int(recovered or 0) / int(total)) if total else 0.0,
        }
        for arm, total, recovered in grouped.all()
    }
    return {
        "total_events": total_events,
        "revenue_at_risk_paise": revenue_at_risk,
        "revenue_recovered_paise": revenue_recovered,
        "recovery_rate": recovered_cases / total_events if total_events else 0.0,
        "by_experiment_arm": by_arm,
    }


@app.get("/api/gateway-health")
async def gateway_health() -> dict:
    redis_client = app.state.redis
    if redis_client is None:
        return {"items": [], "available": False}
    aggregator = GatewayHealthAggregator(redis_client)
    circuit_breaker = GatewayCircuitBreaker(redis_client)
    monitor = DowntimeMonitor(aggregator, circuit_breaker)
    stats = await aggregator.get_all_banks_health()
    snapshots = [
        (await monitor.get_unified_health(item["bank"], item["rail"])).model_dump(mode="json")
        for item in stats
    ]
    return {"items": snapshots, "available": True}


@app.get("/api/experiments/{experiment_id}/results")
async def experiment_results(experiment_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    experiment = await db.scalar(
        select(Experiment).where(Experiment.experiment_id == experiment_id)
    )
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    counts = await db.execute(
        select(
            RecoveryCase.experiment_arm,
            func.count(),
            func.coalesce(
                func.sum(case((RecoveryCase.status == EventStatus.RECOVERED.value, 1), else_=0)),
                0,
            ),
        )
        .where(RecoveryCase.experiment_arm.in_(["control", "treatment"]))
        .group_by(RecoveryCase.experiment_arm)
    )
    grouped = {arm: (int(total or 0), int(recovered or 0)) for arm, total, recovered in counts}
    control_total, control_recovered = grouped.get("control", (0, 0))
    variant_total, variant_recovered = grouped.get("treatment", (0, 0))
    return ExperimentAnalyzer().analyze(
        experiment_id,
        control_recovered,
        control_total,
        variant_recovered,
        variant_total,
    )


@app.post("/api/approvals/{approval_id}/approve")
async def approve(
    approval_id: str, body: ApprovalRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    approval = await _get_approval_or_404(approval_id, db)
    if _is_expired(approval.expires_at):
        raise HTTPException(status_code=409, detail="Approval request has expired")
    approval.status = "APPROVED"
    approval.approved_by = body.approved_by
    approval.approved_at = datetime.now(timezone.utc)
    approval.decision_channel = "api"
    await db.commit()
    queued = await _enqueue_case(app.state.redis, approval.case_id)
    return {"approval_id": approval_id, "status": approval.status, "queued": queued}


@app.post("/api/approvals/{approval_id}/reject")
async def reject(approval_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    approval = await _get_approval_or_404(approval_id, db)
    approval.status = "REJECTED"
    approval.approved_at = datetime.now(timezone.utc)
    approval.decision_channel = "api"
    return {"approval_id": approval_id, "status": approval.status}


@app.post("/api/simulate/batch")
async def simulate_batch(
    body: BatchSimulationRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    events = SyntheticDataGenerator(num_events=body.count).generate_batch()
    case_ids = []
    for event in events:
        case_id = f"REC-SIM-{uuid4().hex[:12].upper()}"
        customer_data = dict(event["customer"])
        customer_data["_revenueguard_context"] = {
            "metadata": event.get("metadata", {}),
            "error_description": event.get("error_description", ""),
        }
        category = _classify_failure(event["error_source"], event["error_reason"])
        db.add(
            RecoveryCase(
                case_id=case_id,
                event_type=str(getattr(event["event_type"], "value", event["event_type"])),
                status=EventStatus.DETECTED.value,
                external_payment_id=event["razorpay_payment_id"],
                external_order_id=event.get("razorpay_order_id"),
                amount_paise=int(event["amount_paise"]),
                currency=event.get("currency", "INR"),
                failure_category=category.value,
                failure_source=event["error_source"],
                failure_reason=event["error_reason"],
                error_code=event["error_code"],
                customer_id=event["customer"]["customer_id"],
                customer_data=customer_data,
                merchant_id=event["merchant_id"],
            )
        )
        case_ids.append(case_id)
    await db.commit()

    queued = 0
    for case_id in case_ids:
        if await _enqueue_case(app.state.redis, case_id):
            queued += 1
        await _emit({"type": "case_created", "case_id": case_id})
    return {"created": len(case_ids), "queued": queued, "case_ids": case_ids}


@app.post("/api/simulate/outage")
async def simulate_outage(body: OutageSimulationRequest) -> dict:
    redis_client = app.state.redis
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis is required to simulate an outage")
    bank = body.bank.strip()
    rail = body.rail.strip().lower()
    aggregator = GatewayHealthAggregator(redis_client)
    for _ in range(60):
        await aggregator.record_outcome(bank, rail, "technical_decline")
    monitor = DowntimeMonitor(aggregator, GatewayCircuitBreaker(redis_client))
    snapshot = await monitor.get_unified_health(bank, rail)
    event = {"type": "gateway_outage", "gateway_health": snapshot.model_dump(mode="json")}
    await _emit(event)
    return event


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket) -> None:
    await connections.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.disconnect(websocket)


async def _create_default_experiment(db: AsyncSession) -> None:
    existing = await db.scalar(
        select(Experiment).where(Experiment.experiment_id == "recovery_agent_v1")
    )
    if existing is None:
        db.add(
            Experiment(
                experiment_id="recovery_agent_v1",
                name="Recovery Agent v1",
                variant_split_pct=get_settings().EXPERIMENT_VARIANT_PCT,
            )
        )


async def _get_case_or_404(case_id: str, db: AsyncSession) -> RecoveryCase:
    case = await db.scalar(select(RecoveryCase).where(RecoveryCase.case_id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    return case


async def _get_approval_or_404(approval_id: str, db: AsyncSession) -> RecoveryApproval:
    approval = await db.scalar(
        select(RecoveryApproval).where(RecoveryApproval.approval_id == approval_id)
    )
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


async def _enqueue_case(redis_client: Any | None, case_id: str) -> bool:
    if redis_client is None:
        return False
    try:
        await redis_client.lpush("recovery_queue", case_id)
        return True
    except Exception:
        return False


async def _emit(event: dict) -> None:
    if not await publish_event(app.state.redis, event):
        await connections.broadcast(event)


async def _case_gateway_health(case_id: str, db: AsyncSession) -> dict | None:
    query = select(GatewayHealthRecord).order_by(GatewayHealthRecord.created_at.desc())
    records = (await db.execute(query)).scalars().all()
    for record in records:
        if record.snapshot_data.get("case_id") == case_id:
            return record.snapshot_data
    return None


def _case_summary(case: RecoveryCase) -> dict:
    return {
        "case_id": case.case_id,
        "status": case.status,
        "event_type": case.event_type,
        "amount_paise": case.amount_paise,
        "currency": case.currency,
        "failure_category": case.failure_category,
        "recovery_probability": case.recovery_probability,
        "experiment_arm": case.experiment_arm,
        "created_at": _iso(case.created_at),
    }


def _case_detail(case: RecoveryCase) -> dict:
    detail = _case_summary(case)
    detail.update(
        {
            "external_payment_id": case.external_payment_id,
            "external_order_id": case.external_order_id,
            "failure_source": case.failure_source,
            "failure_reason": case.failure_reason,
            "error_code": case.error_code,
            "customer_id": case.customer_id,
            "customer": _public_customer(case.customer_data),
            "merchant_id": case.merchant_id,
            "shap_reason_codes": case.shap_reason_codes or [],
            "gateway_health_state": case.gateway_health_state,
            "retry_count": case.retry_count,
            "last_retry_at": _iso(case.last_retry_at),
            "recovered_at": _iso(case.recovered_at),
            "recovered_amount_paise": case.recovered_amount_paise,
            "updated_at": _iso(case.updated_at),
        }
    )
    return detail


def _action_dict(action: RecoveryActionRecord) -> dict:
    return {
        "id": action.id,
        "action_type": action.action_type,
        "channel": action.channel,
        "status": action.status,
        "input_state": action.input_state,
        "output_result": action.output_result,
        "cost_paise": action.cost_paise,
        "created_at": _iso(action.created_at),
    }


def _audit_dict(audit: AuditLog) -> dict:
    return {
        "id": audit.id,
        "action_id": audit.action_id,
        "agent_name": audit.agent_name,
        "step": audit.step,
        "input_summary": audit.input_summary,
        "output_summary": audit.output_summary,
        "reasoning": audit.reasoning,
        "guardrails_applied": audit.guardrails_applied,
        "duration_ms": audit.duration_ms,
        "created_at": _iso(audit.created_at),
    }


def _approval_dict(approval: RecoveryApproval) -> dict:
    return {
        "approval_id": approval.approval_id,
        "status": approval.status,
        "approved_by": approval.approved_by,
        "requested_at": _iso(approval.requested_at),
        "expires_at": _iso(approval.expires_at),
        "approved_at": _iso(approval.approved_at),
    }


def _timeline(case: RecoveryCase, actions: list, audits: list) -> list[dict]:
    timeline = [{"type": "case_created", "at": _iso(case.created_at)}]
    timeline.extend(
        {"type": "action", "action_type": action.action_type, "at": _iso(action.created_at)}
        for action in actions
    )
    timeline.extend(
        {"type": "audit", "step": audit.step, "at": _iso(audit.created_at)} for audit in audits
    )
    return sorted(timeline, key=lambda item: item["at"] or "")


def _public_customer(customer: dict) -> dict:
    return {key: value for key, value in customer.items() if key != "_revenueguard_context"}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _is_expired(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value < datetime.now(timezone.utc)


static_dir = Path("static")
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
