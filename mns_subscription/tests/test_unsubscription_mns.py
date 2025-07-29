import unittest
from unittest.mock import patch, MagicMock
from unsubscribe_mns import run_subscription


class TestRunSubscription(unittest.TestCase):

    @patch("unsubscribe_mns.MnsService")
    @patch("unsubscribe_mns.AppRestrictedAuth")
    @patch("unsubscribe_mns.boto3.client")
    def test_run_subscription_success(self, mock_boto_client, mock_auth_class, mock_mns_service):
        # Arrange
        mock_secrets_client = MagicMock()
        mock_boto_client.return_value = mock_secrets_client

        mock_auth_instance = MagicMock()
        mock_auth_class.return_value = mock_auth_instance

        mock_mns_instance = MagicMock()
        mock_mns_instance.check_delete_subscription.return_value = {"Subscription successfully deleted"}
        mock_mns_service.return_value = mock_mns_instance

        # Act
        result = run_subscription()

        # Assert
        self.assertEqual(result, {"Subscription successfully deleted"})
        mock_auth_class.assert_called_once()
        mock_mns_instance.check_delete_subscription.assert_called_once()


if __name__ == "__main__":
    unittest.main()
