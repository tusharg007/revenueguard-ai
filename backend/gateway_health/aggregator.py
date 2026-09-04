from __future__ import annotations

import time
import uuid
from typing import Any


OUTCOMES = ("success", "technical_decline", "business_decline", "timeout")


class GatewayHealthAggregator:
    """Redis sliding-window aggregator for bank/rail payment health."""

    windows = (5, 15, 60)

    def __init__(self, redis_client: Any):
        self.redis_client = redis_client

    async def record_outcome(self, bank: str, rail: str, outcome: str) -> None:
        if outcome not in OUTCOMES:
            raise ValueError(f"Unsupported gateway outcome: {outcome}")

        now = time.time()
        member = f"{now:.6f}:{uuid.uuid4()}"
        for window in self.windows:
            key = self._key(bank, rail, window, outcome)
            await self.redis_client.zadd(key, {member: now})
            await self.redis_client.zremrangebyscore(key, 0, now - (window * 60))
            await self.redis_client.expire(key, (window * 60) + 60)

    async def get_stats(self, bank: str, rail: str, window_minutes: int = 15) -> dict:
        self._validate_window(window_minutes)
        await self._cleanup_window(bank, rail, window_minutes)

        counts = {}
        for outcome in OUTCOMES:
            counts[outcome] = int(await self.redis_client.zcard(self._key(bank, rail, window_minutes, outcome)))

        total = sum(counts.values())
        return {
            "bank": bank,
            "rail": rail,
            "window_minutes": window_minutes,
            "total_attempts": total,
            "success_rate": self._rate(counts["success"], total),
            "technical_failure_rate": self._rate(counts["technical_decline"] + counts["timeout"], total),
            "business_decline_rate": self._rate(counts["business_decline"], total),
            "timeout_rate": self._rate(counts["timeout"], total),
            "sample_size": total,
        }

    async def get_all_banks_health(self) -> list[dict]:
        stats = []
        async for key in self.redis_client.scan_iter(match="gw:*:*:15m:success"):
            bank, rail = self._parse_success_key(key)
            if bank and rail:
                stats.append(await self.get_stats(bank, rail, window_minutes=15))
        return stats

    async def _cleanup_window(self, bank: str, rail: str, window_minutes: int) -> None:
        cutoff = time.time() - (window_minutes * 60)
        for outcome in OUTCOMES:
            await self.redis_client.zremrangebyscore(self._key(bank, rail, window_minutes, outcome), 0, cutoff)

    @staticmethod
    def _key(bank: str, rail: str, window_minutes: int, outcome: str) -> str:
        return f"gw:{bank}:{rail}:{window_minutes}m:{outcome}"

    @staticmethod
    def _rate(count: int, total: int) -> float:
        return round(count / total, 6) if total else 0.0

    @classmethod
    def _validate_window(cls, window_minutes: int) -> None:
        if window_minutes not in cls.windows:
            raise ValueError(f"Unsupported window: {window_minutes}. Expected one of {list(cls.windows)}")

    @staticmethod
    def _parse_success_key(key: str | bytes) -> tuple[str | None, str | None]:
        text = key.decode("utf-8") if isinstance(key, bytes) else key
        parts = text.split(":")
        if len(parts) != 5 or parts[0] != "gw" or parts[3] != "15m" or parts[4] != "success":
            return None, None
        return parts[1], parts[2]
