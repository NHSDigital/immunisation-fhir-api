import unittest
from unittest.mock import MagicMock, patch

from rate_limiter import FixedWindowRateLimiter


class TestFixedWindowRateLimiter(unittest.TestCase):
    def _limiter(self, redis_client: MagicMock, **kwargs) -> FixedWindowRateLimiter:
        defaults = {
            "key_prefix": "pfx",
            "average_limit": 2,
            "average_window_seconds": 60,
            "spike_limit": 10,
            "spike_window_seconds": 1,
        }
        defaults.update(kwargs)
        return FixedWindowRateLimiter(redis_client, **defaults)

    def _pipeline_mock(self, execute_result: list):
        pipeline = MagicMock()
        pipeline.incr.return_value = pipeline
        pipeline.expire.return_value = pipeline
        pipeline.execute.return_value = execute_result
        return pipeline

    def test_check_allows_when_both_windows_under_limit(self):
        redis_client = MagicMock()
        pipe_avg = self._pipeline_mock([1, True])
        pipe_spike = self._pipeline_mock([2, True])
        redis_client.pipeline.side_effect = [pipe_avg, pipe_spike]

        limiter = self._limiter(redis_client)
        decision = limiter.check("scope-a")

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.window_name, "spike")
        self.assertEqual(decision.count, 2)
        self.assertEqual(redis_client.pipeline.call_count, 2)

    def test_check_denies_on_average_window(self):
        redis_client = MagicMock()
        pipe_avg = self._pipeline_mock([121, True])
        redis_client.pipeline.return_value = pipe_avg

        limiter = self._limiter(redis_client, average_limit=2, average_window_seconds=60)
        decision = limiter.check("scope-b")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.window_name, "average")
        self.assertEqual(decision.count, 121)
        self.assertEqual(decision.limit, 120)
        self.assertEqual(decision.window_seconds, 60)
        redis_client.pipeline.assert_called_once()

    def test_check_denies_on_spike_after_average_passes(self):
        redis_client = MagicMock()
        pipe_avg = self._pipeline_mock([1, True])
        pipe_spike = self._pipeline_mock([11, True])
        redis_client.pipeline.side_effect = [pipe_avg, pipe_spike]

        limiter = self._limiter(redis_client, spike_limit=10)
        decision = limiter.check("scope-c")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.window_name, "spike")
        self.assertEqual(decision.count, 11)
        self.assertEqual(decision.limit, 10)

    def test_evaluate_window_uses_time_bucket_in_key(self):
        redis_client = MagicMock()
        pipeline = self._pipeline_mock([1, True])
        redis_client.pipeline.return_value = pipeline

        limiter = self._limiter(redis_client)
        fixed_t = 1_700_000_000
        window_seconds = 60
        expected_bucket = int(fixed_t // window_seconds)

        with patch("rate_limiter.time.time", return_value=fixed_t):
            decision = limiter._evaluate_window("s", "average", 120, window_seconds)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.count, 1)
        pipeline.incr.assert_called_once()
        incr_key = pipeline.incr.call_args[0][0]
        self.assertIn(f":s:average:{expected_bucket}", incr_key)
        pipeline.expire.assert_called_once_with(incr_key, window_seconds + 1)
