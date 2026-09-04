"""Gateway-health enrichment node with a healthy fallback."""

from __future__ import annotations

from typing import Any

from backend.agents.common import append_audit, metadata_from_case
from backend.agents.state import RecoveryState
from backend.config import get_settings
from backend.gateway_health.aggregator import GatewayHealthAggregator
from backend.gateway_health.circuit_breaker import GatewayCircuitBreaker
from backend.gateway_health.downtime_monitor import DowntimeMonitor
from backend.models.enums import GatewayHealthState
from backend.models.schemas import GatewayHealthSnapshot
from backend.redis_client import create_redis_client


_redis_client: Any | None = None
_monitor: DowntimeMonitor | None = None


def _get_monitor() -> DowntimeMonitor:
    global _monitor, _redis_client
    if _monitor is None:
        _redis_client = create_redis_client(
            get_settings().REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.5,
        )
        aggregator = GatewayHealthAggregator(_redis_client)
        _monitor = DowntimeMonitor(aggregator, GatewayCircuitBreaker(_redis_client))
    return _monitor


async def enrich_with_health(state: RecoveryState) -> dict:
    case = state.get("case_data", {})
    metadata = metadata_from_case(case)
    bank = str(metadata.get("bank_name") or case.get("bank_name") or "unknown")
    rail = str(metadata.get("payment_method") or case.get("payment_method") or "unknown")
    fallback_reason = ""

    try:
        snapshot = await _get_monitor().get_unified_health(bank, rail)
    except Exception as exc:
        fallback_reason = (
            f"Gateway health unavailable ({type(exc).__name__}); healthy default used."
        )
        snapshot = GatewayHealthSnapshot(
            bank=bank,
            rail=rail,
            state=GatewayHealthState.CLOSED,
            success_rate=0.95,
            technical_failure_rate=0.0,
            baseline_success_rate=0.95,
            sample_size=0,
            confidence="LOW",
        )

    health = snapshot.model_dump(mode="json")
    audit = append_audit(
        state,
        "gateway_health",
        "enrich_health",
        f"bank={bank}, rail={rail}",
        f"state={health['state']}, success_rate={health['success_rate']}",
        fallback_reason or "Combined internal sliding-window and processor downtime signals.",
    )
    return {"gateway_health": health, "audit_trail": audit}
