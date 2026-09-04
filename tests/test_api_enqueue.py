import unittest

from backend.redis_client import enqueue_recovery_case


class _TransientRedis:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    async def lpush(self, key: str, case_id: str) -> None:
        self.calls += 1
        if self.calls <= self.failures:
            raise TimeoutError("transient Redis timeout")


class EnqueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_transient_redis_failure(self) -> None:
        client = _TransientRedis(failures=1)

        queued = await enqueue_recovery_case(client, "REC-TEST")

        self.assertTrue(queued)
        self.assertEqual(client.calls, 2)

    async def test_returns_false_after_three_failures(self) -> None:
        client = _TransientRedis(failures=3)

        queued = await enqueue_recovery_case(client, "REC-TEST")

        self.assertFalse(queued)
        self.assertEqual(client.calls, 3)


if __name__ == "__main__":
    unittest.main()
