import unittest
from unittest.mock import patch, MagicMock, Mock, create_autospec
from mns_service import MnsService
from authentication import AppRestrictedAuth
from models.errors import UnhandledResponseError


class TestMnsService(unittest.TestCase):
    def setUp(self):
        # Common mock setup
        self.authenticator = create_autospec(AppRestrictedAuth)
        self.authenticator.get_access_token.return_value = "mocked_token"
        self.mock_secret_manager = Mock()
        self.mock_cache = Mock()

    @patch("mns_service.requests.post")
    def test_successful_subscription(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"subscriptionId": "abc123"}
        mock_post.return_value = mock_response

        service = MnsService(self.authenticator)

        # Act
        result = service.subscribe_notification()

        # Assert
        self.assertEqual(result, {"subscriptionId": "abc123"})
        mock_post.assert_called_once()
        self.authenticator.get_access_token.assert_called_once()

    @patch("mns_service.requests.post")
    def test_not_found_subscription(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        service = MnsService(self.authenticator)
        result = service.subscribe_notification()

        self.assertIsNone(result)

    @patch("mns_service.requests.post")
    def test_unhandled_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Server error"}
        mock_post.return_value = mock_response

        service = MnsService(self.authenticator)

        with self.assertRaises(UnhandledResponseError) as context:
            service.subscribe_notification()

        self.assertIn("Please provide the correct resource type", str(context.exception))


if __name__ == "__main__":
    unittest.main()
