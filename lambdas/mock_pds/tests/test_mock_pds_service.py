import importlib
import json
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("REDIS_HOST", "test-redis-host")
os.environ.setdefault("REDIS_PORT", "6379")

import lambda_handler as lambda_handler_module
from mock_pds_service import RATE_LIMIT_MESSAGE, MockPdsService
from rate_limiter import FixedWindowRateLimiter, RateLimitDecision


def _event(method: str = "GET", nhs_number: str = "9481152782") -> dict:
    return {"rawPath": f"/Patient/{nhs_number}", "requestContext": {"http": {"method": method}}}


def _decision(allowed: bool, count: int) -> RateLimitDecision:
    return RateLimitDecision(allowed=allowed, window_name="spike", count=count, limit=450, window_seconds=1)


class TestMockPdsService(unittest.TestCase):
    def setUp(self):
        self.rate_limiter = Mock(spec=FixedWindowRateLimiter)
        self.rate_limiter.check.return_value = _decision(True, 1)
        self.service = MockPdsService(self.rate_limiter, "Y12345")

    def test_returns_mock_patient_payload(self):
        response = self.service.handle(_event())

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Content-Type"], "application/fhir+json")
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Patient")
        self.assertEqual(body["id"], "9481152782")
        self.assertEqual(body["generalPractitioner"][0]["identifier"]["value"], "Y12345")

    def test_returns_429_when_rate_limit_exceeded(self):
        self.rate_limiter.check.return_value = _decision(False, 451)

        response = self.service.handle(_event())

        self.assertEqual(response["statusCode"], 429)
        self.assertEqual(json.loads(response["body"]), {"code": 429, "message": RATE_LIMIT_MESSAGE})

    def test_rejects_non_get_requests(self):
        response = self.service.handle(_event(method="POST"))

        self.assertEqual(response["statusCode"], 405)


class TestLambdaHandler(unittest.TestCase):
    def tearDown(self):
        importlib.reload(lambda_handler_module)

    @patch.dict(
        "os.environ",
        {
            "REDIS_HOST": "mock-redis",
            "MOCK_PDS_AVERAGE_LIMIT": "125",
            "MOCK_PDS_AVERAGE_WINDOW_SECONDS": "60",
            "MOCK_PDS_SPIKE_LIMIT": "450",
            "MOCK_PDS_SPIKE_WINDOW_SECONDS": "1",
        },
        clear=False,
    )
    @patch("mock_pds_service.MockPdsService")
    @patch("redis.Redis")
    def test_lambda_handler_uses_cached_service(self, mock_redis, mock_pds_cls):
        mock_service = Mock()
        mock_service.handle.return_value = {"statusCode": 200}
        mock_pds_cls.return_value = mock_service

        importlib.reload(lambda_handler_module)
        first_response = lambda_handler_module.lambda_handler(_event(nhs_number="123"), None)
        second_response = lambda_handler_module.lambda_handler(_event(nhs_number="456"), None)

        self.assertEqual(first_response, {"statusCode": 200})
        self.assertEqual(second_response, {"statusCode": 200})
        mock_redis.assert_called_once_with(host="mock-redis", port=6379, decode_responses=True)

    def test_lambda_handler_returns_500_on_unhandled_error(self):
        mock_svc = Mock()
        mock_svc.handle.side_effect = RuntimeError("boom")
        with patch.object(lambda_handler_module, "_mock_pds_service", mock_svc):
            response = lambda_handler_module.lambda_handler(_event(nhs_number="123"), None)

        self.assertEqual(response["statusCode"], 500)
