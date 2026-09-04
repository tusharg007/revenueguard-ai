"""Control-arm recovery strategy."""

from datetime import timedelta

from backend.models.enums import ActionType, RecoveryChannel
from backend.models.schemas import StrategyDecision


RETRY_SCHEDULE = [
    timedelta(minutes=15),
    timedelta(hours=6),
    timedelta(hours=24),
]


def baseline_decide(case: dict, retry_count: int = 0) -> StrategyDecision:
    """Return the fixed retry policy used by the experiment control arm."""
    del case  # The baseline intentionally does not personalize its decisions.

    if retry_count >= len(RETRY_SCHEDULE):
        return StrategyDecision(
            action_type=ActionType.STOP,
            reasoning="Rule-based retry limit reached",
            stopping_reason="Maximum of three baseline retries reached",
        )

    delay = RETRY_SCHEDULE[max(retry_count, 0)]
    return StrategyDecision(
        action_type=ActionType.SMART_RETRY,
        retry_delay_seconds=int(delay.total_seconds()),
        channel=RecoveryChannel.EMAIL,
        reasoning=f"Rule-based retry #{max(retry_count, 0) + 1}",
    )
