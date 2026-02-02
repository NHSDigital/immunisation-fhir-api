import unittest
from unittest.mock import MagicMock, call, patch

from common.api_clients import Constants, raise_error_response, request_with_retry_backoff
from common.models import errors


class TestRaiseErrorResponse(unittest.TestCase):
    def _make_response(self, status_code: int, text="err", json_data=None):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.json.return_value = json_data if json_data is not None else {"error": "something"}
        return response

    @patch("common.api_clients.logger")
    def test_400_raises_bad_request_error(self, mock_logger):
        response = self._make_response(400, text="bad request")

        with self.assertRaises(errors.BadRequestError) as ctx:
            raise_error_response(response)

        self.assertIn("Bad request", str(ctx.exception))
        mock_logger.info.assert_called_once()

    @patch("common.api_clients.logger")
    def test_403_raises_forbidden_error(self, mock_logger):
        response = self._make_response(403, text="forbidden")

        with self.assertRaises(errors.ForbiddenError) as ctx:
            raise_error_response(response)

        self.assertIn("Forbidden", str(ctx.exception))
        mock_logger.info.assert_called_once()

    @patch("common.api_clients.logger")
    def test_500_raises_server_error(self, mock_logger):
        response = self._make_response(500, text="server error")

        with self.assertRaises(errors.ServerError) as ctx:
            raise_error_response(response)

        self.assertIn("Internal Server Error", str(ctx.exception))
        mock_logger.info.assert_called_once()

    @patch("common.api_clients.logger")
    def test_unhandled_status_raises_unhandled_response_error(self, mock_logger):
        response = self._make_response(418, text="I'm a teapot")

        with self.assertRaises(errors.UnhandledResponseError) as ctx:
            raise_error_response(response)

        self.assertIn("Unhandled error: 418", str(ctx.exception))
        mock_logger.info.assert_called_once()

    @patch("common.api_clients.logger")
    def test_404_uses_resource_not_found_error_constructor(self, mock_logger):
        """
        This validates the special-case 404 block:
            raise exception_class(resource_type=response.json(), resource_id=error_message)
        """
        response_json = {"resource": "Patient"}
        response = self._make_response(404, text="not found", json_data=response_json)

        with self.assertRaises(errors.ResourceNotFoundError) as ctx:
            raise_error_response(response)

        # Here we validate the exception received those specific args
        exc = ctx.exception
        self.assertEqual(exc.resource_type, response_json)
        self.assertEqual(exc.resource_id, "Resource not found")
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
