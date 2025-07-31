import unittest
import os
from unittest.mock import patch, MagicMock, Mock, create_autospec
from mns_service import MnsService, MNS_URL
from authentication import AppRestrictedAuth
from models.errors import (
    ServerError,
    UnhandledResponseError,
    TokenValidationError,
    BadRequestError,
    UnauthorizedError,
    ResourceNotFoundError)


SQS_ARN = "arn:aws:sqs:eu-west-2:123456789012:my-queue"


@patch("mns_service.SQS_ARN", SQS_ARN)
class TestMnsService(unittest.TestCase):
    def setUp(self):
        # Common mock setup
        self.authenticator = create_autospec(AppRestrictedAuth)
        self.authenticator.get_access_token.return_value = "mocked_token"
        self.mock_secret_manager = Mock()
        self.mock_cache = Mock()
        self.sqs = SQS_ARN

    @patch("mns_service.requests.post")
    @patch("mns_service.requests.get")
    def test_successful_subscription(self, mock_get, mock_post):

        # Arrange GET to return no subscription found
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"entry": []}
        mock_get.return_value = mock_get_response

        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"subscriptionId": "abc123"}
        mock_post.return_value = mock_response

        service = MnsService(self.authenticator)

        # Act
        result = service.check_subscription()

        # Assert
        self.assertEqual(result, {"subscriptionId": "abc123"})
        mock_post.assert_called_once()
        mock_get.assert_called_once()
        self.authenticator.get_access_token.assert_called_once()

    @patch("mns_service.requests.post")
    def test_not_found_subscription(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        service = MnsService(self.authenticator)

        with self.assertRaises(ResourceNotFoundError) as context:
            service.subscribe_notification()
        self.assertIn("Subscription or Resource not found", str(context.exception))

    @patch("mns_service.requests.post")
    def test_unhandled_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Server error"}
        mock_post.return_value = mock_response

        service = MnsService(self.authenticator)

        with self.assertRaises(ServerError) as context:
            service.subscribe_notification()

        self.assertIn("Internal Server Error", str(context.exception))

    @patch.dict(os.environ, {"SQS_ARN": "arn:aws:sqs:eu-west-2:123456789012:my-queue"})
    @patch("mns_service.requests.get")
    def test_get_subscription_success(self, mock_get):
        """Should return the resource dict when a matching subscription exists."""
        # Arrange a bundle with a matching entry
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry": [
                {
                    "channel": {
                        "endpoint": SQS_ARN
                    },
                    "id": "123"
                    }]
                }
        mock_get.return_value = mock_response

        service = MnsService(self.authenticator)
        result2 = service.get_subscription()
        self.assertIsNotNone(result2)
        self.assertEqual(result2["channel"]["endpoint"], SQS_ARN)

    @patch("mns_service.requests.get")
    def test_get_subscription_no_match(self, mock_get):
        """Should return None when no subscription matches."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry": []}
        mock_get.return_value = mock_response

        service = MnsService(self.authenticator)
        result = service.get_subscription()
        self.assertIsNone(result)

    @patch("mns_service.requests.get")
    def test_get_subscription_401(self, mock_get):
        """Should raise TokenValidationError for 401."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"fault": {"faultstring": "Invalid Access Token"}}
        mock_get.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(TokenValidationError):
            service.get_subscription()

    @patch("mns_service.requests.post")
    @patch("mns_service.requests.get")
    def test_check_subscription_creates_if_not_found(self, mock_get, mock_post):
        """If GET finds nothing, POST is called and returned."""
        # Arrange GET returns no match
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"entry": []}
        mock_get.return_value = mock_get_response

        # Arrange POST returns a new subscription
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"subscriptionId": "abc123"}
        mock_post.return_value = mock_post_response

        service = MnsService(self.authenticator)
        result = service.check_subscription()
        self.assertEqual(result, {"subscriptionId": "abc123"})
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    @patch("mns_service.requests.delete")
    def test_delete_subscription_success(self, mock_delete):
        for code in (200, 204):
            mock_response = MagicMock()
            mock_response.status_code = code
            mock_delete.return_value = mock_response

            service = MnsService(self.authenticator)
            result = service.delete_subscription("sub-id-123")
            self.assertTrue(result)
            mock_delete.assert_called_with(
                f"{MNS_URL}/sub-id-123",
                headers=service.request_headers,
                timeout=10
            )

    @patch("mns_service.requests.delete")
    def test_delete_subscription_401(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "token"}
        mock_delete.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(TokenValidationError):
            service.delete_subscription("sub-id-123")

    @patch("mns_service.requests.delete")
    def test_delete_subscription_403(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "forbidden"}
        mock_delete.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(UnauthorizedError):
            service.delete_subscription("sub-id-123")

    @patch("mns_service.requests.delete")
    def test_delete_subscription_404(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "not found"}
        mock_delete.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(ResourceNotFoundError):
            service.delete_subscription("sub-id-123")

    @patch("mns_service.requests.delete")
    def test_delete_subscription_500(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "server"}
        mock_delete.return_value = mock_response

        service = MnsService(self.authenticator)
        with self.assertRaises(ServerError):
            service.delete_subscription("sub-id-123")

    @patch("mns_service.requests.delete")
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
        result = service.check_delete_subcription()
        self.assertEqual(result, "Subscription successfully deleted")
        mock_get_subscription.assert_called_once()
        mock_delete_subscription.assert_called_once_with("sub-123")

    @patch.object(MnsService, "get_subscription")
    def test_check_delete_subscription_no_resource(self, mock_get_subscription):
        # No subscription found
        mock_get_subscription.return_value = None
        service = MnsService(self.authenticator)
        result = service.check_delete_subcription()
        self.assertEqual(result, "No matching subscription found to delete.")

    @patch.object(MnsService, "get_subscription")
    def test_check_delete_subscription_missing_id(self, mock_get_subscription):
        # Resource with no id field
        mock_get_subscription.return_value = {"not_id": "not-id"}
        service = MnsService(self.authenticator)
        result = service.check_delete_subcription()
        self.assertEqual(result, "Subscription resource missing 'id' field.")

    @patch.object(MnsService, "delete_subscription")
    @patch.object(MnsService, "get_subscription")
    def test_check_delete_subscription_raises(self, mock_get_subscription, mock_delete_subscription):
        mock_get_subscription.return_value = {"id": "sub-123"}
        mock_delete_subscription.side_effect = Exception("Error!")
        service = MnsService(self.authenticator)
        result = service.check_delete_subcription()
        self.assertTrue(result.startswith("Error deleting subscription: Error!"))

    def mock_response(self, status_code, json_data=None):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data or {"resource": "mock"}
        return mock_resp

    def test_404_resource_found_error(self):
        resp = self.mock_response(404, {"resource": "Not found"})
        with self.assertRaises(ResourceNotFoundError) as context:
            MnsService.handle_response(resp)
        self.assertIn("Subscription or Resource not found", str(context.exception))
        self.assertEqual(context.exception.message, "Subscription or Resource not found")
        self.assertEqual(context.exception.response, {"resource": "Not found"})

    def test_400_bad_request_error(self):
        resp = self.mock_response(400, {"resource": "Invalid"})
        with self.assertRaises(BadRequestError) as context:
            MnsService.handle_response(resp)
        self.assertIn("Bad request: Resource type or parameters incorrect", str(context.exception))
        self.assertEqual(context.exception.message, "Bad request: Resource type or parameters incorrect")
        self.assertEqual(context.exception.response, {"resource": "Invalid"})

    def test_unhandled_status_code(self):
        resp = self.mock_response(418, {"resource": 1234})
        with self.assertRaises(UnhandledResponseError) as context:
            MnsService.handle_response(resp)
        self.assertIn("Unhandled error: 418", str(context.exception))
        self.assertEqual(context.exception.response, {"resource": 1234})


if __name__ == "__main__":
    unittest.main()
