"""Per-segment Thompson Sampling channel selection."""

from __future__ import annotations

from collections.abc import Iterable

from mabwiser.mab import LearningPolicy, MAB


class ChannelBandit:
    """Learn the best recovery channel independently for each customer segment."""

    arms = ["sms", "email", "whatsapp"]

    def __init__(self) -> None:
        self.segment_bandits: dict[str, MAB] = {}

    def get_or_create_bandit(self, segment: str) -> MAB:
        if segment not in self.segment_bandits:
            bandit = MAB(self.arms, LearningPolicy.ThompsonSampling())
            # One success and one failure per arm yields the same neutral posterior
            # for every channel before segment-specific outcomes arrive.
            decisions = [arm for arm in self.arms for _ in range(2)]
            rewards = [reward for _ in self.arms for reward in (1, 0)]
            bandit.fit(decisions, rewards)
            self.segment_bandits[segment] = bandit
        return self.segment_bandits[segment]

    def select_channel(
        self, segment: str, eligible_channels: Iterable[str] | None = None
    ) -> str:
        expectations = self.get_expectations(segment)
        eligible = self._eligible_channels(eligible_channels)
        return max(eligible, key=lambda channel: expectations[channel])

    def update(self, segment: str, channel: str, recovered: bool) -> None:
        if channel not in self.arms:
            raise ValueError(f"Unsupported channel: {channel}")
        self.get_or_create_bandit(segment).partial_fit(
            decisions=[channel], rewards=[1 if recovered else 0]
        )

    def get_expectations(self, segment: str) -> dict[str, float]:
        expectations = self.get_or_create_bandit(segment).predict_expectations()
        return {channel: float(expectations[channel]) for channel in self.arms}

    @staticmethod
    def segment_customer(customer: dict) -> str:
        """Build a compact segment from language, LTV, and WhatsApp eligibility."""
        language = str(customer.get("preferred_language", "en")).strip().lower() or "en"
        lifetime_value = int(customer.get("lifetime_value_paise", 0) or 0)
        ltv_bucket = "high" if lifetime_value >= 1_000_000 else "low"

        explicit_eligibility = customer.get("whatsapp_eligible")
        has_phone = bool(customer.get("phone"))
        eligible_for_whatsapp = (
            explicit_eligibility if explicit_eligibility is not None else has_phone
        ) and not bool(customer.get("opted_out", False))
        whatsapp_bucket = "wa" if eligible_for_whatsapp else "nowa"
        return f"{language}_{ltv_bucket}_{whatsapp_bucket}"

    def _eligible_channels(self, eligible_channels: Iterable[str] | None) -> list[str]:
        if eligible_channels is None:
            return list(self.arms)

        eligible = list(dict.fromkeys(eligible_channels))
        unknown = set(eligible).difference(self.arms)
        if unknown:
            raise ValueError(f"Unsupported eligible channels: {sorted(unknown)}")
        if not eligible:
            raise ValueError("At least one eligible channel is required")
        return eligible
