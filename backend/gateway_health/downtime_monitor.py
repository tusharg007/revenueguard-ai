from __future__ import annotations

from typing import Any

from backend.gateway_health.aggregator import GatewayHealthAggregator
from backend.gateway_health.circuit_breaker import GatewayCircuitBreaker
from backend.integrations import razorpay_client as default_razorpay_client
from backend.models.enums import GatewayHealthState
from backend.models.schemas import GatewayHealthSnapshot


class DowntimeMonitor:
    def __init__(
        self,
        aggregator: GatewayHealthAggregator,
        circuit_breaker: GatewayCircuitBreaker,
        razorpay_client: Any | None = None,
    ):
        self.aggregator = aggregator
        self.circuit_breaker = circuit_breaker
        self.razorpay_client = razorpay_client or default_razorpay_client

    async def get_unified_health(self, bank: str, rail: str) -> GatewayHealthSnapshot:
        stats = await self.aggregator.get_stats(bank, rail)
        internal = await self.circuit_breaker.get_health(bank, rail, stats)

        try:
            downtimes = self.razorpay_client.fetch_downtimes()
        except Exception:
            downtimes = []

        if any(self._downtime_matches(item, bank, rail) for item in downtimes):
            return self._downtime_override(internal)
        return internal

    @staticmethod
    def _downtime_override(snapshot: GatewayHealthSnapshot) -> GatewayHealthSnapshot:
        data = snapshot.model_dump()
        data.update(
            {
                "state": GatewayHealthState.OPEN,
                "recommended_action": "DEFER",
                "retry_after_seconds": max(snapshot.retry_after_seconds, 600),
                "confidence": "HIGH",
            }
        )
        return GatewayHealthSnapshot(**data)

    @staticmethod
    def _downtime_matches(downtime: dict, bank: str, rail: str) -> bool:
        if not isinstance(downtime, dict):
            return False

        status = str(downtime.get("status", downtime.get("state", "active"))).lower()
        if status in {"resolved", "completed", "inactive", "up"}:
            return False

        bank_value = DowntimeMonitor._flatten_values(
            downtime,
            ("bank", "bank_name", "issuer", "issuer_name", "institution", "provider"),
        )
        rail_value = DowntimeMonitor._flatten_values(
            downtime,
            ("rail", "method", "payment_method", "network", "instrument", "gateway"),
        )

        bank_match = not bank_value or bank.lower() in bank_value or bank_value in bank.lower()
        rail_match = not rail_value or rail.lower() in rail_value or rail_value in rail.lower()
        return bank_match and rail_match

    @staticmethod
    def _flatten_values(payload: dict, keys: tuple[str, ...]) -> str:
        values = []
        for key in keys:
            value = payload.get(key)
            if isinstance(value, dict):
                values.extend(str(v) for v in value.values() if v is not None)
            elif isinstance(value, list):
                values.extend(str(v) for v in value if v is not None)
            elif value is not None:
                values.append(str(value))
        return " ".join(values).lower()
