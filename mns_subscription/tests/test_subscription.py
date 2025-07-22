import unittest
from unittest.mock import patch, MagicMock, create_autospec
from subscribe_mns import MnsService, AppRestrictedAuth


class TestMainSubscriptionCall(unittest.TestCase):
    
    def setUp(self):
        # Common mock setup
        self.authenticator = create_autospec(AppRestrictedAuth)
        self.authenticator.get_access_token.return_value = "mocked_token"
    
    @patch("subscribe_mns.MnsService")
    def test_main_subscription_call(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"subscriptionId": "abc123"}
        mock_post.return_value = mock_response

        mns = MnsService(authenticator=self.authenticator)

        # Act
        result = mns.subscribeNotification()

        # Assert
        self.assertEqual(result, {"subscriptionId": "abc123"})
        mock_post.assert_called_once()
        self.authenticator.get_access_token.assert_called_once()

if __name__ == "__main__":
    unittest.main()