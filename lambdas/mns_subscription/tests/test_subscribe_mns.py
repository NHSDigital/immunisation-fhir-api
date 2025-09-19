import unittest
from unittest.mock import patch, MagicMock
from subscribe_mns import run_subscription


class TestRunSubscription(unittest.TestCase):

    @patch("subscribe_mns.get_mns_service")  # patch where it's imported/used!
    def test_run_subscription_success(self, mock_get_mns_service):
        mock_mns_instance = MagicMock()
        mock_mns_instance.check_subscription.return_value = "Subscription Result: abc123"
        mock_get_mns_service.return_value = mock_mns_instance

        result = run_subscription()

        self.assertEqual(result, "Subscription Result: abc123")
        mock_get_mns_service.assert_called_once()
        mock_mns_instance.check_subscription.assert_called_once()


if __name__ == "__main__":
    unittest.main()
