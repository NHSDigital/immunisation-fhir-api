import logging
import os

import redis

from mock_pds_service import MockPdsService
from rate_limiter import FixedWindowRateLimiter

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_redis_client = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)
_rate_limiter = FixedWindowRateLimiter(
    redis_client=_redis_client,
    key_prefix="mock-pds",
    average_limit=int(os.getenv("MOCK_PDS_AVERAGE_LIMIT", "125")),
    average_window_seconds=int(os.getenv("MOCK_PDS_AVERAGE_WINDOW_SECONDS", "60")),
    spike_limit=int(os.getenv("MOCK_PDS_SPIKE_LIMIT", "450")),
    spike_window_seconds=int(os.getenv("MOCK_PDS_SPIKE_WINDOW_SECONDS", "1")),
)
_mock_pds_service = MockPdsService(_rate_limiter, os.getenv("MOCK_PDS_GP_ODS_CODE", "Y12345"))


def lambda_handler(event, context):
    try:
        return _mock_pds_service.handle(event)
    except Exception:
        logger.exception("Mock PDS failed to handle request")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": '{"code": 500, "message": "Mock PDS encountered an unexpected error"}',
        }
