from __future__ import annotations

import json
import time
from typing import Any

from backend.models.enums import GatewayHealthState
from backend.models.schemas import GatewayHealthSnapshot


class GatewayCircuitBreaker:
    def __init__(
        self,
        redis_client: Any,
        failure_threshold: float = 0.30,
        min_samples: int = 50,
        cooldown_seconds: int = 600,
        probe_count: int = 3,
        probe_required_successes: int = 2,
    ):
        self.redis_client = redis_client
        self.failure_threshold = failure_threshold
        self.min_samples = min_samples
        self.cooldown_seconds = cooldown_seconds
        self.probe_count = probe_count
        self.probe_required_successes = probe_required_successes

    async def evaluate(self, bank: str, rail: str, stats: dict) -> GatewayHealthState:
        state = await self._get_state(bank, rail)
        now = time.time()
        current = GatewayHealthState(state.get("state", GatewayHealthState.CLOSED.value))
        sample_size = int(stats.get("sample_size", stats.get("total_attempts", 0)) or 0)
        technical_failure_rate = float(stats.get("technical_failure_rate", 0.0) or 0.0)

        if current == GatewayHealthState.CLOSED:
            if sample_size > self.min_samples and technical_failure_rate > self.failure_threshold:
                state = self._new_state(GatewayHealthState.OPEN, now, cooldown_seconds=self.cooldown_seconds)
                await self._save_state(bank, rail, state)
                return GatewayHealthState.OPEN
            await self._save_state(bank, rail, state)
            return GatewayHealthState.CLOSED

        if current == GatewayHealthState.OPEN:
            opened_at = float(state.get("opened_at", state.get("updated_at", now)) or now)
            cooldown = int(state.get("cooldown_seconds", self.cooldown_seconds) or self.cooldown_seconds)
            if now - opened_at >= cooldown:
                state = self._new_state(GatewayHealthState.HALF_OPEN, now, cooldown_seconds=cooldown)
                await self._save_state(bank, rail, state)
                return GatewayHealthState.HALF_OPEN
            return GatewayHealthState.OPEN

        if current == GatewayHealthState.HALF_OPEN:
            probe_successes = int(state.get("probe_successes", 0) or 0)
            probe_failures = int(state.get("probe_failures", 0) or 0)
            required_failures = max(1, self.probe_count - self.probe_required_successes + 1)
            if probe_successes >= self.probe_required_successes:
                state = self._new_state(GatewayHealthState.CLOSED, now, cooldown_seconds=self.cooldown_seconds)
                await self._save_state(bank, rail, state)
                return GatewayHealthState.CLOSED
            if probe_failures >= required_failures:
                cooldown = int(state.get("cooldown_seconds", self.cooldown_seconds) or self.cooldown_seconds) * 2
                state = self._new_state(GatewayHealthState.OPEN, now, cooldown_seconds=cooldown)
                await self._save_state(bank, rail, state)
                return GatewayHealthState.OPEN
            return GatewayHealthState.HALF_OPEN

        return GatewayHealthState.CLOSED

    async def record_probe_result(self, bank: str, rail: str, success: bool) -> None:
        state = await self._get_state(bank, rail)
        current = GatewayHealthState(state.get("state", GatewayHealthState.CLOSED.value))
        if current != GatewayHealthState.HALF_OPEN:
            return

        field = "probe_successes" if success else "probe_failures"
        state[field] = int(state.get(field, 0) or 0) + 1
        state["updated_at"] = time.time()
        await self._save_state(bank, rail, state)

    async def get_health(self, bank: str, rail: str, stats: dict) -> GatewayHealthSnapshot:
        state = await self.evaluate(bank, rail, stats)
        stored = await self._get_state(bank, rail)
        retry_after_seconds = 0
        recommended_action = "RETRY_NOW"

        if state == GatewayHealthState.OPEN:
            recommended_action = "DEFER"
            opened_at = float(stored.get("opened_at", stored.get("updated_at", time.time())) or time.time())
            cooldown = int(stored.get("cooldown_seconds", self.cooldown_seconds) or self.cooldown_seconds)
            retry_after_seconds = max(0, int(cooldown - (time.time() - opened_at)))
        elif state == GatewayHealthState.HALF_OPEN:
            recommended_action = "PROBE"

        sample_size = int(stats.get("sample_size", stats.get("total_attempts", 0)) or 0)
        return GatewayHealthSnapshot(
            bank=bank,
            rail=rail,
            state=state,
            success_rate=float(stats.get("success_rate", 0.0) or 0.0),
            technical_failure_rate=float(stats.get("technical_failure_rate", 0.0) or 0.0),
            business_decline_rate=float(stats.get("business_decline_rate", 0.0) or 0.0),
            timeout_rate=float(stats.get("timeout_rate", 0.0) or 0.0),
            baseline_success_rate=self._baseline_success_rate(stats),
            sample_size=sample_size,
            window_minutes=int(stats.get("window_minutes", 15) or 15),
            recommended_action=recommended_action,
            retry_after_seconds=retry_after_seconds,
            confidence=self._confidence(sample_size),
        )

    async def _get_state(self, bank: str, rail: str) -> dict:
        raw = await self.redis_client.get(self._key(bank, rail))
        if raw is None:
            return self._new_state(GatewayHealthState.CLOSED, time.time(), cooldown_seconds=self.cooldown_seconds)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return self._new_state(GatewayHealthState.CLOSED, time.time(), cooldown_seconds=self.cooldown_seconds)

    async def _save_state(self, bank: str, rail: str, state: dict) -> None:
        state["updated_at"] = time.time()
        await self.redis_client.set(self._key(bank, rail), json.dumps(state))

    @staticmethod
    def _key(bank: str, rail: str) -> str:
        return f"cb:{bank}:{rail}"

    @staticmethod
    def _new_state(state: GatewayHealthState, now: float, cooldown_seconds: int) -> dict:
        payload = {
            "state": state.value,
            "updated_at": now,
            "cooldown_seconds": cooldown_seconds,
            "probe_successes": 0,
            "probe_failures": 0,
        }
        if state == GatewayHealthState.OPEN:
            payload["opened_at"] = now
        return payload

    @staticmethod
    def _baseline_success_rate(stats: dict) -> float:
        return float(stats.get("baseline_success_rate", 0.95) or 0.95)

    def _confidence(self, sample_size: int) -> str:
        if sample_size >= self.min_samples:
            return "HIGH"
        if sample_size >= max(10, self.min_samples // 2):
            return "MEDIUM"
        return "LOW"
