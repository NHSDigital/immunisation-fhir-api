import os
import unittest
from unittest.mock import MagicMock, Mock, create_autospec, patch

from common.api_clients.authentication import AppRestrictedAuth
from common.api_clients.errors import (
    BadRequestError,
    ForbiddenError,
    ResourceNotFoundError,
    ServerError,
    TokenValidationError,
    UnhandledResponseError,
    raise_error_response,
)
from common.api_clients.mns_service import MNS_URL, MnsService

SQS_ARN = "arn:aws:sqs:eu-west-2:123456789012:my-queue"


@patch("common.api_clients.mns_service.SQS_ARN", SQS_ARN)
class TestMnsService(unittest.TestCase):
    def setUp(self):
        # Common mock setup
        self.authenticator = create_autospec(AppRestrictedAuth)
        self.authenticator.get_access_token.return_value = "mocked_token"
        self.mock_secret_manager = Mock()
        self.mock_cache = Mock()
        self.sqs = SQS_ARN

    @patch("common.api_clients.mns_service.requests.request")
    def test_successful_subscription(self, mock_request):
        # Arrange GET to return no subscription found
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"entry": []}

        # Arrange POST to return created subscription
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"subscriptionId": "abc123"}

        # Mock returns GET response first, then POST response
        mock_request.side_effect = [mock_get_response, mock_post_response]

        service = MnsService(self.authenticator)

        # Act
        result = service.check_subscription()

        # Assert
        self.assertEqual(result, {"subscriptionId": "abc123"})
        self.assertEqual(mock_request.call_count, 2)
        self.authenticator.get_access_token.assert_called_once()

    @patch("common.api_clients.mns_service.requests.request")
    def test_not_found_subscription(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        service = MnsService(self.authenticator)

        with self.assertRaises(ResourceNotFoundError) as context:
            service.subscribe_notification()
        self.assertIn("Resource not found", str(context.exception))

    @patch("common.api_clients.mns_service.requests.request")
    def test_unhandled_error(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Server error"}
        mock_request.return_value = mock_response

        service = MnsService(self.authenticator)

        with self.assertRaises(ServerError) as context:
            service.subscribe_notification()

        self.assertIn("Internal Server Error", str(context.exception))

    @patch.dict(os.environ, {"SQS_ARN": "arn:aws:sqs:eu-west-2:123456789012:my-queue"})
    @patch("common.api_clients.mns_service.requests.request")
    def test_get_subscription_success(self, mock_get):
        """Should return the resource dict when a matching subscription exists."""
        # Arrange a bundle with a matching entry
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry": [{"channel": {"endpoint": SQS_ARN}, "id": "123"}]}
        mock_get.return_value = mock_response

        service = MnsService(self.authenticator)
        result2 = service.get_subscription()
        self.assertIsNotNone(result2)
        self.assertEqual(result2["channel"]["endpoint"], SQS_ARN)

    @patch("common.api_clients.mns_service.requests.request")
    def test_get_subscription_no_match(self, mock_get):
        """Should return None when no subscription matches."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry": []}
        mock_get.return_value = mock_response

        service = MnsService(self.authenticator)
        result = service.get_subscription()
        self.assertIsNone(result)

    @patch("common.api_clients.mns_service.requests.request")
    def test_get_subscription_401(self, mock_get):
        """Should raise TokenValidationError for 401."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"fault": {"faultstring": "Invalid Access Token"}}
        mock_get.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(TokenValidationError):
            service.get_subscription()

    @patch("common.api_clients.mns_service.requests.request")
    def test_check_subscription_creates_if_not_found(self, mock_request):
        """If GET finds nothing, POST is called and returned."""
        # Arrange GET returns no match
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"entry": []}

        # Arrange POST returns a new subscription
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"subscriptionId": "abc123"}

        # Mock returns GET response first, then POST response
        mock_request.side_effect = [mock_get_response, mock_post_response]

        service = MnsService(self.authenticator)
        result = service.check_subscription()
        self.assertEqual(result, {"subscriptionId": "abc123"})
        self.assertEqual(mock_request.call_count, 2)

    @patch("common.api_clients.mns_service.requests.request")
    def test_delete_subscription_success(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        service = MnsService(self.authenticator)
        result = service.delete_subscription("sub-id-123")
        self.assertTrue(result)
        mock_delete.assert_called_with(
            method="DELETE", url=f"{MNS_URL}/subscriptions/sub-id-123", headers=service.request_headers, timeout=10
        )

    @patch("common.api_clients.mns_service.requests.request")
    def test_delete_subscription_401(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "token"}
        mock_delete.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(TokenValidationError):
            service.delete_subscription("sub-id-123")

    @patch("common.api_clients.mns_service.requests.request")
    def test_delete_subscription_403(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "forbidden"}
        mock_delete.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(ForbiddenError):
            service.delete_subscription("sub-id-123")

    @patch("common.api_clients.mns_service.requests.request")
    def test_delete_subscription_404(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "not found"}
        mock_delete.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(ResourceNotFoundError):
            service.delete_subscription("sub-id-123")

    @patch("common.api_clients.mns_service.requests.request")
    def test_delete_subscription_500(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "server"}
        mock_delete.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(ServerError):
            service.delete_subscription("sub-id-123")

    @patch("common.api_clients.mns_service.requests.request")
    def test_delete_subscription_unhandled(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 418  # Unhandled status code
        mock_response.json.return_value = {"error": "teapot"}
        mock_delete.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(UnhandledResponseError):
            service.delete_subscription("sub-id-123")

    @patch.object(MnsService, "delete_subscription")
    @patch.object(MnsService, "get_subscription")
    def test_check_delete_subscription_success(self, mock_get_subscription, mock_delete_subscription):
        # Mock get_subscription returns a resource with id
        mock_get_subscription.return_value = {"id": "sub-123"}
        # Mock delete_subscription returns True
        mock_delete_subscription.return_value = True

        service = MnsService(self.authenticator)
        result = service.check_delete_subscription()
        self.assertEqual(result, "Subscription successfully deleted")
        mock_get_subscription.assert_called_once()
        mock_delete_subscription.assert_called_once_with("sub-123")

    @patch.object(MnsService, "get_subscription")
    def test_check_delete_subscription_no_resource(self, mock_get_subscription):
        # No subscription found
        mock_get_subscription.return_value = None
        service = MnsService(self.authenticator)
        result = service.check_delete_subscription()
        self.assertEqual(result, "No matching subscription found to delete.")

    @patch.object(MnsService, "get_subscription")
    def test_check_delete_subscription_missing_id(self, mock_get_subscription):
        # Resource with no id field
        mock_get_subscription.return_value = {"not_id": "not-id"}
        service = MnsService(self.authenticator)
        result = service.check_delete_subscription()
        self.assertEqual(result, "Subscription resource missing 'id' field.")

    @patch.object(MnsService, "delete_subscription")
    @patch.object(MnsService, "get_subscription")
    def test_check_delete_subscription_raises(self, mock_get_subscription, mock_delete_subscription):
        mock_get_subscription.return_value = {"id": "sub-123"}
        mock_delete_subscription.side_effect = Exception("Error!")
        service = MnsService(self.authenticator)
        result = service.check_delete_subscription()
        self.assertTrue(result.startswith("Error deleting subscription: Error!"))

    def mock_response(self, status_code, json_data=None):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data or {"resource": "mock"}
        return mock_resp

    def test_404_resource_found_error(self):
        resp = self.mock_response(404, {"resource": "Not found"})
        with self.assertRaises(ResourceNotFoundError) as context:
            raise_error_response(resp)
        self.assertIn("Resource not found", str(context.exception))
        self.assertEqual(context.exception.message, "Resource not found")
        self.assertEqual(context.exception.response, {"resource": "Not found"})

    def test_400_bad_request_error(self):
        resp = self.mock_response(400, {"resource": "Invalid"})
        with self.assertRaises(BadRequestError) as context:
            raise_error_response(resp)
        self.assertIn("Bad request", str(context.exception))
        self.assertEqual(
            context.exception.message,
            "Bad request",
        )
        self.assertEqual(context.exception.response, {"resource": "Invalid"})

    def test_unhandled_status_code(self):
        resp = self.mock_response(418, {"resource": 1234})
        with self.assertRaises(UnhandledResponseError) as context:
            raise_error_response(resp)
        self.assertIn("Unhandled error: 418", str(context.exception))
        self.assertEqual(context.exception.response, {"resource": 1234})

    @patch("common.api_clients.mns_service.requests.request")
    def test_publish_notification_success(self, mock_request):
        """Test successful notification publishing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "published"}
        mock_request.return_value = mock_response

        notification_payload = {
            "specversion": "1.0",
            "id": "test-id",
            "type": "imms-vaccinations-2",
            "source": "test-source",
        }

        service = MnsService(self.authenticator)
        result = service.publish_notification(notification_payload)

        self.assertEqual(result["status"], "published")
        self.assertEqual(service.request_headers["Content-Type"], "application/cloudevents+json")
        mock_request.assert_called_once()

    @patch("common.api_clients.mns_service.requests.request")
    @patch("common.api_clients.mns_service.raise_error_response")
    def test_publish_notification_failure(self, mock_raise_error, mock_request):
        """Test notification publishing failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_request.return_value = mock_response

        notification_payload = {"id": "test-id"}

        service = MnsService(self.authenticator)
        service.publish_notification(notification_payload)

        mock_raise_error.assert_called_once_with(mock_response)


if __name__ == "__main__":
    unittest.main()
