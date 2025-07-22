import unittest
from unittest.mock import patch, MagicMock
from subscribe_mns import run_subscription


class TestRunSubscription(unittest.TestCase):

    @patch("subscribe_mns.MnsService")
    @patch("subscribe_mns.AppRestrictedAuth")
    @patch("subscribe_mns.boto3.client")
    def test_run_subscription_success(self, mock_boto_client, mock_auth_class, mock_mns_service):
        # Arrange
        mock_secrets_client = MagicMock()
        mock_boto_client.return_value = mock_secrets_client

        mock_auth_instance = MagicMock()
        mock_auth_class.return_value = mock_auth_instance

        mock_mns_instance = MagicMock()
        mock_mns_instance.subscribeNotification.return_value = {"subscriptionId": "abc123"}
        mock_mns_service.return_value = mock_mns_instance

        # Act
        result = run_subscription()

        # Assert
        self.assertEqual(result, {"subscriptionId": "abc123"})
        mock_auth_class.assert_called_once()
        mock_mns_service.assert_called_once_with(mock_auth_instance, "int")
        mock_mns_instance.subscribeNotification.assert_called_once()


if __name__ == "__main__":
    unittest.main()
