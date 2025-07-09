import unittest
from unittest.mock import patch
from models.utils.permissions import get_supplier_permissions


class TestPermissions(unittest.TestCase):

    @patch("redis_client.redis_client.hget")
    def test_returns_list_if_permissions_exist(self, mock_hget):
        mock_hget.return_value = '["COVID19.CRUDS", "FLU.C"]'
        result = get_supplier_permissions("DPSFULL")
        self.assertEqual(result, ["COVID19.CRUDS", "FLU.C"])

    @patch("redis_client.redis_client.hget")
    def test_returns_empty_list_if_no_permissions(self, mock_hget):
        mock_hget.return_value = None
        result = get_supplier_permissions("UNKNOWN")
        self.assertEqual(result, [])
