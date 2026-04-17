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
        self.average_limit = average_limit
        self.average_window_seconds = average_window_seconds
        self.spike_limit = spike_limit
        self.spike_window_seconds = spike_window_seconds

    def check(self, scope: str) -> RateLimitDecision:
        average_decision = self._evaluate_window(
            scope=scope,
            window_name="average",
            limit=self.average_limit * self.average_window_seconds,
            window_seconds=self.average_window_seconds,
        )
        if not average_decision.allowed:
            return average_decision

        return self._evaluate_window(
            scope=scope,
            window_name="spike",
            limit=self.spike_limit,
            window_seconds=self.spike_window_seconds,
        )

    def _evaluate_window(self, scope: str, window_name: str, limit: int, window_seconds: int) -> RateLimitDecision:
        current_window = int(time.time() // window_seconds)
        key = f"{self.key_prefix}:{scope}:{window_name}:{current_window}"
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
