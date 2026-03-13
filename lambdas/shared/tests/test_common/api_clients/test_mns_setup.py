import unittest
from unittest.mock import MagicMock, patch

from common.api_clients.mns_setup import get_mns_service


class TestGetMnsService(unittest.TestCase):
    @patch("common.api_clients.mns_setup.get_secrets_manager_client")
    @patch("common.api_clients.mns_setup.AppRestrictedAuth")
    @patch("common.api_clients.mns_setup.MnsService")
    def test_get_mns_service(self, mock_mns_service, mock_app_auth, mock_get_secrets_manager_client):
        # Arrange
        mock_auth_instance = MagicMock()
        mock_app_auth.return_value = mock_auth_instance

        mock_mns_instance = MagicMock()
        mock_mns_service.return_value = mock_mns_instance

        mock_secrets_client = MagicMock()
        mock_get_secrets_manager_client.return_value = mock_secrets_client

        # Act
        result = get_mns_service("int")

        # Assert
        self.assertEqual(result, mock_mns_instance)
        mock_get_secrets_manager_client.assert_called_once_with()
        mock_app_auth.assert_called_once()
        mock_mns_service.assert_called_once_with(mock_auth_instance)


if __name__ == "__main__":
    unittest.main()
