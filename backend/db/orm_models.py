import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.database import Base
from backend.db.types import UTCDateTime


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    razorpay_event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    processed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=True)


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"
    __table_args__ = (
        Index("ix_recovery_cases_status", "status"),
        Index("ix_recovery_cases_event_type", "event_type"),
        Index("ix_recovery_cases_created_at", "created_at"),
        Index("ix_recovery_cases_experiment_arm", "experiment_arm"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="detected")
    external_payment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    failure_category: Mapped[str] = mapped_column(String(50), nullable=False)
    failure_source: Mapped[str] = mapped_column(String(50), nullable=False)
    failure_reason: Mapped[str] = mapped_column(String(255), default="")
    error_code: Mapped[str] = mapped_column(String(100), default="")
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    recovery_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    shap_reason_codes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    experiment_arm: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gateway_health_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_retry_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    recovered_amount_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, onupdate=_now, nullable=True)


class RecoveryActionRecord(Base):
    __tablename__ = "recovery_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("recovery_cases.case_id"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    input_state: Mapped[dict] = mapped_column(JSON, default=dict)
    output_result: Mapped[dict] = mapped_column(JSON, default=dict)
    cost_paise: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("recovery_cases.case_id"), nullable=False, index=True
    )
    action_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("recovery_actions.id"), nullable=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    step: Mapped[str] = mapped_column(String(100), nullable=False)
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output_summary: Mapped[str] = mapped_column(Text, default="")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    guardrails_applied: Mapped[list] = mapped_column(JSON, default=list)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class GatewayHealthRecord(Base):
    __tablename__ = "gateway_health_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    bank: Mapped[str] = mapped_column(String(50), nullable=False)
    rail: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False)
    technical_failure_rate: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    control_version: Mapped[str] = mapped_column(String(100), default="naive_retry_v1")
    variant_version: Mapped[str] = mapped_column(String(100), default="recovery_agent_v1")
    variant_split_pct: Mapped[int] = mapped_column(Integer, default=20)
    min_sample_size: Mapped[int] = mapped_column(Integer, default=1000)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class ExperimentAssignmentRecord(Base):
    __tablename__ = "experiment_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("experiments.experiment_id"), nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("recovery_cases.case_id"), nullable=False
    )
    arm: Mapped[str] = mapped_column(String(20), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class ExperimentResultRecord(Base):
    __tablename__ = "experiment_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("experiments.experiment_id"), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    control_value: Mapped[float] = mapped_column(Float, nullable=False)
    variant_value: Mapped[float] = mapped_column(Float, nullable=False)
    delta: Mapped[float] = mapped_column(Float, nullable=False)
    ci_lower: Mapped[float] = mapped_column(Float, default=0.0)
    ci_upper: Mapped[float] = mapped_column(Float, default=0.0)
    p_value: Mapped[float] = mapped_column(Float, nullable=False)
    is_significant: Mapped[bool] = mapped_column(Boolean, default=False)
    sample_size_control: Mapped[int] = mapped_column(Integer, default=0)
    sample_size_variant: Mapped[int] = mapped_column(Integer, default=0)
    calculated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class RecoveryApproval(Base):
    __tablename__ = "recovery_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    approval_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    case_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("recovery_cases.case_id"), nullable=False, index=True
    )
    payment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_action: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_recommendation: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    requested_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    decision_channel: Mapped[str | None] = mapped_column(String(50), nullable=True)


class ChannelBanditState(Base):
    __tablename__ = "channel_bandit_state"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    segment: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    bandit_state: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now, onupdate=_now)
