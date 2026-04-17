import json
import unittest
from unittest.mock import Mock, patch

from lambda_handler import get_mock_pds_service, lambda_handler
from mock_pds_service import RATE_LIMIT_MESSAGE, MockPdsService
from rate_limiter import FixedWindowRateLimiter, RateLimitDecision


class TestMockPdsService(unittest.TestCase):
    def setUp(self):
        self.rate_limiter = Mock(spec=FixedWindowRateLimiter)
        self.rate_limiter.check.return_value = RateLimitDecision(
            allowed=True,
            window_name="spike",
            count=1,
            limit=450,
            window_seconds=1,
        )
        self.service = MockPdsService(self.rate_limiter, "Y12345")

    def test_returns_mock_patient_payload(self):
        response = self.service.handle({"rawPath": "/Patient/9481152782", "requestContext": {"http": {"method": "GET"}}})

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Content-Type"], "application/fhir+json")
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Patient")
        self.assertEqual(body["id"], "9481152782")
        self.assertEqual(body["generalPractitioner"][0]["identifier"]["value"], "Y12345")

    def test_returns_429_when_rate_limit_exceeded(self):
        self.rate_limiter.check.return_value = RateLimitDecision(
            allowed=False,
            window_name="spike",
            count=451,
            limit=450,
            window_seconds=1,
        )

        response = self.service.handle({"rawPath": "/Patient/9481152782", "requestContext": {"http": {"method": "GET"}}})

        self.assertEqual(response["statusCode"], 429)
        self.assertEqual(json.loads(response["body"]), {"code": 429, "message": RATE_LIMIT_MESSAGE})

    def test_rejects_non_get_requests(self):
        response = self.service.handle(
            {"rawPath": "/Patient/9481152782", "requestContext": {"http": {"method": "POST"}}}
        )

        self.assertEqual(response["statusCode"], 405)


class TestLambdaHandler(unittest.TestCase):
    def tearDown(self):
        get_mock_pds_service.__globals__["_mock_pds_service"] = None

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
    @patch("lambda_handler.redis.Redis")
    def test_lambda_handler_uses_cached_service(self, mock_redis):
        mock_service = Mock()
        mock_service.handle.return_value = {"statusCode": 200}

        with patch("lambda_handler.MockPdsService", return_value=mock_service):
            first_response = lambda_handler(
                {"rawPath": "/Patient/123", "requestContext": {"http": {"method": "GET"}}}, None
            )
            second_response = lambda_handler(
                {"rawPath": "/Patient/456", "requestContext": {"http": {"method": "GET"}}}, None
            )

        self.assertEqual(first_response, {"statusCode": 200})
        self.assertEqual(second_response, {"statusCode": 200})
        mock_redis.assert_called_once_with(host="mock-redis", port=6379, decode_responses=True)

    @patch("lambda_handler.get_mock_pds_service")
    def test_lambda_handler_returns_500_on_unhandled_error(self, mock_get_service):
        mock_get_service.return_value.handle.side_effect = RuntimeError("boom")

        response = lambda_handler({"rawPath": "/Patient/123", "requestContext": {"http": {"method": "GET"}}}, None)

        self.assertEqual(response["statusCode"], 500)
