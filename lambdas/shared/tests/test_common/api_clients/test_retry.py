import unittest
from unittest.mock import MagicMock, call, patch

import requests

from common.api_clients.constants import Constants
from common.api_clients.errors import (
    BadRequestError,
    ForbiddenError,
    ServerError,
    UnhandledResponseError,
    raise_error_response,
)
from common.api_clients.retry import request_with_retry_backoff


class TestRaiseErrorResponse(unittest.TestCase):
    def _make_response(self, status_code: int, text="err", json_data=None):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.json.return_value = json_data if json_data is not None else {"error": "something"}
        return response

    @patch("common.api_clients.errors.logger")
    def test_400_raises_bad_request_error(self, mock_logger):
        response = self._make_response(400, text="bad request")

        with self.assertRaises(BadRequestError) as ctx:
            raise_error_response(response)

        self.assertIn("Bad request", str(ctx.exception))
        mock_logger.info.assert_called_once()

    @patch("common.api_clients.errors.logger")
    def test_403_raises_forbidden_error(self, mock_logger):
        response = self._make_response(403, text="forbidden")

        with self.assertRaises(ForbiddenError) as ctx:
            raise_error_response(response)

        self.assertIn("Forbidden", str(ctx.exception))
        mock_logger.info.assert_called_once()

    @patch("common.api_clients.errors.logger")
    def test_500_raises_server_error(self, mock_logger):
        response = self._make_response(500, text="server error")

        with self.assertRaises(ServerError) as ctx:
            raise_error_response(response)

        self.assertIn("Internal Server Error", str(ctx.exception))
        mock_logger.info.assert_called_once()

    @patch("common.api_clients.errors.logger")
    def test_unhandled_status_raises_unhandled_response_error(self, mock_logger):
        response = self._make_response(418, text="I'm a teapot")

        with self.assertRaises(UnhandledResponseError) as ctx:
            raise_error_response(response)

        self.assertIn("Unhandled error: 418", str(ctx.exception))
        mock_logger.info.assert_called_once()


def _make_response(status_code: int, text: str = "err"):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    return response


class TestRequestWithRetryBackoff(unittest.TestCase):
    @patch("time.sleep")
    @patch("requests.request")
    def test_returns_immediately_for_non_retryable_status(self, mock_get, mock_sleep):
        # Arrange
        mock_get.return_value = _make_response(400)
        # Ensure retryable codes include 429/5xx only (example)
        with patch.object(Constants, "RETRYABLE_STATUS_CODES", {429, 500, 502, 503, 504}):
            # Act
            resp = request_with_retry_backoff("GET", "http://example.com", {})

        # Assert
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(mock_get.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    @patch("requests.request")
    def test_retries_until_exhausted_for_retryable_status(self, mock_get, mock_sleep):
        # Arrange: always retryable => should attempt 1 + max_retries times
        mock_get.side_effect = [
            _make_response(503),
            _make_response(503),
            _make_response(503),
        ]
        with patch.object(Constants, "RETRYABLE_STATUS_CODES", {429, 500, 502, 503, 504}):
            # Act
            resp = request_with_retry_backoff("GET", "http://example.com", {})

        # Assert
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(mock_get.call_count, 3)  # 1 initial + 2 retries
        self.assertEqual(mock_sleep.call_count, 2)  # sleep between retries only

    @patch("time.sleep")
    @patch("requests.request")
    def test_stops_retrying_when_non_retryable_received(self, mock_get, mock_sleep):
        # Arrange: retryable twice, then success => should stop
        mock_get.side_effect = [
            _make_response(503),
            _make_response(503),
            _make_response(200, text="ok"),
        ]
        with patch.object(Constants, "RETRYABLE_STATUS_CODES", {429, 500, 502, 503, 504}):
            # Act
            resp = request_with_retry_backoff("GET", "http://example.com", {})

        # Assert
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("time.sleep")
    @patch("requests.request")
    def test_backoff_values_are_exponential(self, mock_get, mock_sleep):
        # Arrange: always retryable
        mock_get.side_effect = [
            _make_response(503),
            _make_response(503),
            _make_response(503),
        ]
        with patch.object(Constants, "RETRYABLE_STATUS_CODES", {429, 500, 502, 503, 504}):
            # Act
            request_with_retry_backoff("GET", "http://example.com", {})

        # Assert: 0.5, 1.0 for attempts 0 and 1
        mock_sleep.assert_has_calls(
            [call(Constants.API_CLIENTS_BACKOFF_SECONDS), call(Constants.API_CLIENTS_BACKOFF_SECONDS * 2)]
        )


class TestRequestWithRetryBackoffNetworkErrors(unittest.TestCase):
    """
    Regression tests for the ReadTimeout incident (imms-blue-id-sync-lambda-error, 17 Mar 2026).
    Verifies that network-level exceptions are retried identically to retryable HTTP status codes.
    """

    @patch("time.sleep")
    @patch("requests.request")
    def test_read_timeout_is_retried(self, mock_request, mock_sleep):
        """ReadTimeout on attempt 1 then success on attempt 2 — must not raise."""
        mock_request.side_effect = [
            requests.exceptions.ReadTimeout("read timeout=5"),
            _make_response(200),
        ]

        resp = request_with_retry_backoff("GET", "http://example.com", {})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 1)

    @patch("time.sleep")
    @patch("requests.request")
    def test_connection_error_is_retried(self, mock_request, mock_sleep):
        """ConnectionError on attempt 1 then success on attempt 2 — must not raise."""
        mock_request.side_effect = [
            requests.exceptions.ConnectionError("connection refused"),
            _make_response(200),
        ]

        resp = request_with_retry_backoff("GET", "http://example.com", {})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_request.call_count, 2)

    @patch("time.sleep")
    @patch("requests.request")
    def test_timeout_exhausted_raises_after_max_retries(self, mock_request, mock_sleep):
        """
        ReadTimeout on every attempt — must raise after max_retries+1 total attempts.
        With API_CLIENTS_MAX_RETRIES=2, that is 3 attempts total.
        """
        mock_request.side_effect = requests.exceptions.ReadTimeout("read timeout=5")

        with self.assertRaises(requests.exceptions.ReadTimeout):
            request_with_retry_backoff("GET", "http://example.com", {})

        self.assertEqual(mock_request.call_count, Constants.API_CLIENTS_MAX_RETRIES + 1)

    @patch("time.sleep")
    @patch("requests.request")
    def test_timeout_retry_backoff_is_exponential(self, mock_request, mock_sleep):
        """Sleep intervals between network-error retries must be identical to HTTP retryable backoff."""
        mock_request.side_effect = requests.exceptions.ReadTimeout("read timeout=5")

        with self.assertRaises(requests.exceptions.ReadTimeout):
            request_with_retry_backoff("GET", "http://example.com", {})

        mock_sleep.assert_has_calls(
            [
                call(Constants.API_CLIENTS_BACKOFF_SECONDS),  # after attempt 1: 0.5s
                call(Constants.API_CLIENTS_BACKOFF_SECONDS * 2),  # after attempt 2: 1.0s
            ]
        )

    @patch("time.sleep")
    @patch("requests.request")
    def test_timeout_then_retryable_status_then_success(self, mock_request, mock_sleep):
        """Network error on attempt 1, HTTP 503 on attempt 2, success on attempt 3 — full coverage."""
        mock_request.side_effect = [
            requests.exceptions.ReadTimeout("read timeout=5"),
            _make_response(503),
            _make_response(200),
        ]

        resp = request_with_retry_backoff("GET", "http://example.com", {})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_request.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
