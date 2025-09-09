import unittest
from unittest.mock import patch, MagicMock
from unsubscribe_mns import run_unsubscribe


class TestRunUnsubscribe(unittest.TestCase):

    @patch("unsubscribe_mns.get_mns_service")
    def test_run_unsubscribe_success(self, mock_get_mns_service):
        # Arrange
        mock_mns_instance = MagicMock()
        mock_mns_instance.check_delete_subscription.return_value = "Subscription successfully deleted"
        mock_get_mns_service.return_value = mock_mns_instance

        # Act
        result = run_unsubscribe()

        # Assert
        self.assertEqual(result, "Subscription successfully deleted")
        mock_get_mns_service.assert_called_once()
        mock_mns_instance.check_delete_subscription.assert_called_once()


if __name__ == "__main__":
    unittest.main()
