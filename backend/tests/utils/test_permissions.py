import unittest
from unittest.mock import patch
from src.models.utils.permissions import get_supplier_permissions

class TestPermissions(unittest.TestCase):

    @patch("clients.redis_client.hget")
    def test_returns_list_if_permissions_exist(self, mock_hget):
        mock_hget.return_value = '["COVID19_FULL", "FLU_CREATE"]'
        result = get_supplier_permissions("DPSFULL")
        self.assertEqual(result, ["COVID19_FULL", "FLU_CREATE"])

    @patch("clients.redis_client.hget")
    def test_returns_empty_list_if_no_permissions(self, mock_hget):
        mock_hget.return_value = None
        result = get_supplier_permissions("UNKNOWN")
        self.assertEqual(result, [])