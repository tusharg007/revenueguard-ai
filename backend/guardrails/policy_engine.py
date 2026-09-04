"""Deterministic recovery policy checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.agents.common import append_audit, customer_from_case, enum_value
from backend.agents.state import RecoveryState
from backend.config import get_settings
from backend.models.enums import ActionType
from backend.models.schemas import StrategyDecision


class ApprovalRequired(RuntimeError):
    """Raised when a high-value action lacks a valid approval."""


class PolicyEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    def check_all(self, state: RecoveryState) -> tuple[bool, str | None]:
        case = state.get("case_data", {})
        strategy = state.get("strategy") or {}
        action = enum_value(strategy.get("action_type"))
        customer = customer_from_case(case)

        if customer.get("opted_out", False) and action != ActionType.STOP.value:
            return False, "Customer opted out"

        retry_count = int(case.get("retry_count", case.get("prior_retry_count", 0)) or 0)
        if retry_count >= self.settings.MAX_RETRY_ATTEMPTS and action != ActionType.STOP.value:
            return False, "Maximum retry attempts reached"

        amount_paise = int(case.get("amount_paise", 0) or 0)
        if amount_paise < 10_000 and action not in {
            ActionType.STOP.value,
            ActionType.ESCALATE_HUMAN.value,
        }:
            return False, "Recovery amount is below INR 100 cost threshold"

        if action in self._contact_or_retry_actions():
            last_retry = self._parse_datetime(case.get("last_retry_at"))
            if last_retry is not None:
                elapsed = datetime.now(timezone.utc) - last_retry
                if elapsed < timedelta(hours=self.settings.COOLDOWN_HOURS):
                    return False, "Recovery cooldown is still active"

        if action in self._customer_contact_actions():
            hour = datetime.now(ZoneInfo("Asia/Kolkata")).hour
            start = self.settings.QUIET_HOURS_START
            end = self.settings.QUIET_HOURS_END
            in_quiet_hours = hour >= start or hour < end if start > end else start <= hour < end
            if in_quiet_hours:
                return False, "Customer contact blocked during quiet hours"

        return True, None

    def needs_approval(self, state: RecoveryState) -> bool:
        amount = int(state.get("case_data", {}).get("amount_paise", 0) or 0)
        action = enum_value((state.get("strategy") or {}).get("action_type"))
        return (
            amount > self.settings.HIGH_VALUE_THRESHOLD
            and action != ActionType.STOP.value
            and not self.has_valid_approval(state)
        )

    def has_valid_approval(self, state: RecoveryState) -> bool:
        if str(state.get("approval_status") or "").upper() != "APPROVED":
            return False
        approval = state.get("approval_record") or {}
        expires_at = approval.get("expires_at")
        if not expires_at:
            return True
        expiry = self._parse_datetime(expires_at)
        return expiry is not None and expiry > datetime.now(timezone.utc)

    def assert_approved(self, state: RecoveryState) -> None:
        if self.needs_approval(state):
            raise ApprovalRequired("Valid approval required for high-value recovery action")

    @staticmethod
    def _parse_datetime(value) -> datetime | None:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _customer_contact_actions() -> set[str]:
        return {
            ActionType.PAYMENT_LINK.value,
            ActionType.NUDGE_EMAIL.value,
            ActionType.NUDGE_SMS.value,
            ActionType.NUDGE_WHATSAPP.value,
        }

    @classmethod
    def _contact_or_retry_actions(cls) -> set[str]:
        return cls._customer_contact_actions() | {ActionType.SMART_RETRY.value}


async def policy_check_node(state: RecoveryState) -> dict:
    engine = PolicyEngine()
    allowed, reason = engine.check_all(state)
    if not allowed:
        strategy = StrategyDecision(
            action_type=ActionType.STOP,
            reasoning=f"Policy blocked recovery: {reason}",
            stopping_reason=reason,
        ).model_dump(mode="json")
        audit = append_audit(
            state,
            "policy_engine",
            "policy_check",
            f"requested_action={(state.get('strategy') or {}).get('action_type')}",
            "action=stop",
            reason or "Policy check failed",
            guardrails=[reason] if reason else [],
        )
        return {"strategy": strategy, "needs_approval": False, "audit_trail": audit}

    approval_needed = engine.needs_approval(state)
    audit = append_audit(
        state,
        "policy_engine",
        "policy_check",
        f"action={(state.get('strategy') or {}).get('action_type')}",
        f"allowed=true, needs_approval={approval_needed}",
        "All deterministic policy checks passed.",
        guardrails=["opt_out", "retry_limit", "cooldown", "quiet_hours", "recovery_cost"],
    )
    return {"needs_approval": approval_needed, "audit_trail": audit}
