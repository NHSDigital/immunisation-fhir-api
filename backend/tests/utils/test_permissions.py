import unittest
from unittest.mock import patch
from models.constants import Constants

from models.utils.permissions import get_supplier_permissions

class TestGetSupplierPermissions(unittest.TestCase):
    
    def setUp(self):
        self.redis_client_patcher = patch("models.utils.permissions.redis_client")
        self.mock_redis_client = self.redis_client_patcher.start()
    
    def tearDown(self):
        patch.stopall()
    
    def test_returns_permissions_list(self):
        # Arrange
        supplier = "supplier-1"
        self.mock_redis_client.hget.return_value = '["perm1", "perm2"]'
        # Act
        result = get_supplier_permissions(supplier)
        # Assert
        self.assertEqual(result, ["perm1", "perm2"])
        self.mock_redis_client.hget.assert_called_once_with(Constants.SUPPLIER_PERMISSIONS_KEY, supplier)

    def test_returns_empty_list_when_no_permissions(self):
        # Arrange
        supplier = "supplier-2"
        self.mock_redis_client.hget.return_value = None
        # Act
        result = get_supplier_permissions(supplier)
        # Assert
        self.assertEqual(result, [])
        self.mock_redis_client.hget.assert_called_once_with(Constants.SUPPLIER_PERMISSIONS_KEY, supplier)

    def test_returns_empty_list_when_empty_string(self):
        # Arrange
        supplier = "supplier-3"
        self.mock_redis_client.hget.return_value = ""
        # Act
        result = get_supplier_permissions(supplier)
        # Assert
        self.assertEqual(result, [])
        self.mock_redis_client.hget.assert_called_once_with(Constants.SUPPLIER_PERMISSIONS_KEY, supplier)