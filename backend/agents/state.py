"""Shared state contract for the recovery graph."""

from typing import TypedDict


class RecoveryState(TypedDict, total=False):
    case_id: str
    case_data: dict
    triage: dict | None
    gateway_health: dict | None
    experiment_arm: str | None
    diagnosis: dict | None
    strategy: dict | None
    selected_channel: str | None
    actions: list[dict]
    needs_approval: bool
    approval_status: str | None
    audit_trail: list[dict]
    error: str | None
    final_decision: str | None
    approval_record: dict | None
