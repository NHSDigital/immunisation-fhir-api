import time
from dataclasses import dataclass

import redis


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    window_name: str
    count: int
    limit: int
    window_seconds: int


class FixedWindowRateLimiter:
    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str,
        average_limit: int,
        average_window_seconds: int,
        spike_limit: int,
        spike_window_seconds: int,
    ):
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        self._windows = (
            ("average", average_limit * average_window_seconds, average_window_seconds),
            ("spike", spike_limit, spike_window_seconds),
        )

    def check(self, scope: str) -> RateLimitDecision:
        decision = None
        for name, limit, seconds in self._windows:
            decision = self._evaluate_window(scope, name, limit, seconds)
            if not decision.allowed:
                break
        return decision

    def _evaluate_window(self, scope: str, window_name: str, limit: int, window_seconds: int) -> RateLimitDecision:
        key = f"{self.key_prefix}:{scope}:{window_name}:{int(time.time() // window_seconds)}"
        pipeline = self.redis_client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, window_seconds + 1)
        count, _ = pipeline.execute()

        return RateLimitDecision(
            allowed=count <= limit,
            window_name=window_name,
            count=count,
            limit=limit,
            window_seconds=window_seconds,
        )
