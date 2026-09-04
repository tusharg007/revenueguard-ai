import unittest

from backend.agents.strategy_node import _normalize_strategy_payload
from backend.models.schemas import StrategyDecision


class StrategyDecisionTests(unittest.TestCase):
    def test_nullable_llm_retry_delay_is_normalized(self) -> None:
        payload = {
            "action_type": "smart_retry",
            "reasoning": "Retry after a transient failure.",
            "retry_delay_seconds": None,
        }
        decision = StrategyDecision(**_normalize_strategy_payload(payload))

        self.assertEqual(decision.retry_delay_seconds, 0)


if __name__ == "__main__":
    unittest.main()
