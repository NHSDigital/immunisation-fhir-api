import unittest
from unittest.mock import patch, MagicMock
from mns_setup import get_mns_service


class TestGetMnsService(unittest.TestCase):

    @patch("mns_setup.boto3.client")
    @patch("mns_setup.AppRestrictedAuth")
    @patch("mns_setup.MnsService")
    def test_get_mns_service(self, mock_mns_service, mock_app_auth, mock_boto_client):
        # Arrange
        mock_auth_instance = MagicMock()
        mock_app_auth.return_value = mock_auth_instance

        mock_mns_instance = MagicMock()
        mock_mns_service.return_value = mock_mns_instance

        mock_secrets_client = MagicMock()
        mock_boto_client.return_value = mock_secrets_client

        # Act
        result = get_mns_service("int")

        # Assert
        self.assertEqual(result, mock_mns_instance)
        mock_boto_client.assert_called_once_with("secretsmanager", config=mock_boto_client.call_args[1]['config'])
        mock_app_auth.assert_called_once()
        mock_mns_service.assert_called_once_with(mock_auth_instance)


if __name__ == "__main__":
    unittest.main()
