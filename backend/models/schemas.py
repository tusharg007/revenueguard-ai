from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.models.enums import (
    ActionType,
    EventStatus,
    EventType,
    ExperimentArm,
    FailureCategory,
    FailureSource,
    GatewayHealthState,
    Priority,
    RecoveryChannel,
)


class CustomerProfile(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: str
    upi_id: str | None = None
    preferred_language: str = "en"
    lifetime_value_paise: int = 0
    total_transactions: int = 0
    failed_transactions: int = 0
    last_payment_date: datetime | None = None
    opted_out: bool = False


class NormalizedFailureEvent(BaseModel):
    case_id: str
    event_type: EventType
    processor: str = "razorpay"
    external_payment_id: str
    external_order_id: str | None = None
    amount_paise: int
    currency: str = "INR"
    category: FailureCategory
    source: FailureSource
    stage: str
    reason: str
    error_code: str
    error_description: str
    customer: CustomerProfile
    merchant_id: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class TriageResult(BaseModel):
    recovery_probability: float
    expected_recovery_paise: int
    priority: Priority
    shap_reason_codes: list[str] = Field(default_factory=list)
    shap_feature_importances: dict[str, float] = Field(default_factory=dict)
    model_version: str = "v1"


class GatewayHealthSnapshot(BaseModel):
    bank: str
    rail: str
    state: GatewayHealthState
    success_rate: float
    technical_failure_rate: float
    business_decline_rate: float = 0.0
    timeout_rate: float = 0.0
    baseline_success_rate: float = 0.95
    sample_size: int
    window_minutes: int = 15
    recommended_action: str = "RETRY_NOW"
    retry_after_seconds: int = 0
    confidence: str = "HIGH"


class DiagnosisResult(BaseModel):
    root_cause: str
    is_transient: bool
    failure_category: str
    reasoning: str
    time_sensitivity: str = "hours"


class StrategyDecision(BaseModel):
    action_type: ActionType
    channel: RecoveryChannel | None = None
    reasoning: str = ""
    retry_delay_seconds: int = 0
    message_content: str | None = None
    payment_link_amount_paise: int | None = None
    escalation_reason: str | None = None
    stopping_reason: str | None = None


class RecoveryAction(BaseModel):
    action_id: str
    case_id: str
    action_type: ActionType
    channel: RecoveryChannel | None = None
    status: str = "pending"
    input_state: dict[str, Any] = Field(default_factory=dict)
    output_result: dict[str, Any] = Field(default_factory=dict)
    cost_paise: int = 0
    timestamp: datetime
    idempotency_key: str


class ExperimentAssignment(BaseModel):
    experiment_id: str
    case_id: str
    arm: ExperimentArm
    assigned_at: datetime


class ApprovalRecord(BaseModel):
    approval_id: str
    case_id: str
    payment_id: str
    amount_paise: int
    requested_action: ActionType
    agent_recommendation: str
    status: str = "PENDING"
    requested_at: datetime
    expires_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None
    decision_channel: str | None = None


class AuditLogEntry(BaseModel):
    id: str
    case_id: str
    action_id: str | None = None
    agent_name: str
    step: str
    input_summary: str
    output_summary: str
    reasoning: str = ""
    timestamp: datetime
    guardrails_applied: list[str] = Field(default_factory=list)
    duration_ms: int = 0


class RecoveryMetrics(BaseModel):
    total_events: int = 0
    revenue_at_risk_paise: int = 0
    revenue_recovered_paise: int = 0
    recovery_rate: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    false_positive_cost_paise: int = 0
    avg_time_to_recovery_hours: float = 0.0
    exceptions_count: int = 0
