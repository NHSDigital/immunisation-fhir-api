import unittest
import os
from unittest.mock import patch, MagicMock, Mock, create_autospec
from mns_service import MnsService
from authentication import AppRestrictedAuth
from models.errors import ServerError, UnhandledResponseError, TokenValidationError


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
        mock_get_response.json.return_value = {"entry": []}  # No entries!
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

        with self.assertRaises(UnhandledResponseError) as context:
            service.subscribe_notification()
        self.assertIn("404", str(context.exception))
        self.assertIn("Unhandled error", str(context.exception))

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
        mock_response.json.return_value = {"entry": []}  # No matches
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

    # Similarly, you can add tests for 400, 403, 500, etc.

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
        mock_get_subscription.return_value = {"not_id": "nope"}
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


if __name__ == "__main__":
    unittest.main()
