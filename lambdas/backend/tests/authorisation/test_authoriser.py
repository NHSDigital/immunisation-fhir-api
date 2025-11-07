import unittest
from unittest.mock import Mock, patch

from authorisation.api_operation_code import ApiOperationCode
from authorisation.authoriser import Authoriser


class TestAuthoriser(unittest.TestCase):
    MOCK_SUPPLIER_NAME = "TestSupplier"

    def setUp(self):
        self.mock_redis = Mock()
        self.cache_client_patcher = patch("authorisation.authoriser.get_redis_client")
        self.mock_cache_client = self.cache_client_patcher.start()

        self.logger_patcher = patch("authorisation.authoriser.logger")
        self.mock_logger = self.logger_patcher.start()

        self.test_authoriser = Authoriser()

    def tearDown(self):
        patch.stopall()

    def test_authorise_returns_true_if_supplier_has_permissions(self):
        """Authoriser().authorise should return true if the supplier has the required permissions"""
        self.mock_redis.hget.return_value = '["COVID.RS"]'
        self.mock_cache_client.return_value = self.mock_redis

        result = self.test_authoriser.authorise(self.MOCK_SUPPLIER_NAME, ApiOperationCode.READ, {"COVID"})

        self.assertTrue(result)
        self.mock_redis.hget.assert_called_once_with("supplier_permissions", self.MOCK_SUPPLIER_NAME)
        self.mock_logger.info.assert_called_once_with(
            "operation: r, supplier_permissions: {'covid': ['r', 's']}, vaccine_types: {'COVID'}"
        )

    def test_authorise_returns_false_if_supplier_does_not_have_any_permissions(self):
        """Authoriser().authorise should return false if the supplier does not have any permissions in the cache"""
        self.mock_redis.hget.return_value = ""
        self.mock_cache_client.return_value = self.mock_redis

        result = self.test_authoriser.authorise(self.MOCK_SUPPLIER_NAME, ApiOperationCode.CREATE, {"COVID"})

        self.assertFalse(result)
        self.mock_redis.hget.assert_called_once_with("supplier_permissions", self.MOCK_SUPPLIER_NAME)
        self.mock_logger.info.assert_called_once_with("operation: c, supplier_permissions: {}, vaccine_types: {'COVID'}")

    def test_authorise_returns_false_if_supplier_does_not_have_permission_for_operation(
        self,
    ):
        """Authoriser().authorise should return false if the supplier does not have permission for the operation"""
        self.mock_redis.hget.return_value = '["COVID.RS"]'
        self.mock_cache_client.return_value = self.mock_redis

        result = self.test_authoriser.authorise(self.MOCK_SUPPLIER_NAME, ApiOperationCode.CREATE, {"COVID"})

        self.assertFalse(result)
        self.mock_redis.hget.assert_called_once_with("supplier_permissions", self.MOCK_SUPPLIER_NAME)
        self.mock_logger.info.assert_called_once_with(
            "operation: c, supplier_permissions: {'covid': ['r', 's']}, vaccine_types: {'COVID'}"
        )

    def test_authorise_returns_false_if_no_permission_for_vaccination_type(self):
        """Authoriser().authorise should return false if the supplier does not have permission for the vaccination
        type"""
        self.mock_redis.hget.return_value = '["COVID.RS"]'
        self.mock_cache_client.return_value = self.mock_redis

        result = self.test_authoriser.authorise(self.MOCK_SUPPLIER_NAME, ApiOperationCode.READ, {"FLU"})

        self.assertFalse(result)
        self.mock_redis.hget.assert_called_once_with("supplier_permissions", self.MOCK_SUPPLIER_NAME)
        self.mock_logger.info.assert_called_once_with(
            "operation: r, supplier_permissions: {'covid': ['r', 's']}, vaccine_types: {'FLU'}"
        )

    def test_authorise_returns_false_multiple_vaccs_scenario(self):
        """Authoriser().authorise should return false if the supplier is missing a permission for any of the vaccs in
        the list provided"""
        self.mock_redis.hget.return_value = '["COVID.RS", "FLU.CRUDS"]'
        self.mock_cache_client.return_value = self.mock_redis

        result = self.test_authoriser.authorise(self.MOCK_SUPPLIER_NAME, ApiOperationCode.READ, {"FLU", "COVID", "RSV"})

        self.assertFalse(result)
        self.mock_redis.hget.assert_called_once_with("supplier_permissions", self.MOCK_SUPPLIER_NAME)

    def test_filter_permitted_vacc_types_returns_all_if_supplier_has_perms_for_all(
        self,
    ):
        """The same set of vaccination types will be returned if the supplier has the required permissions"""
        self.mock_redis.hget.return_value = '["COVID.RS", "FLU.CRUDS", "RSV.CRUDS"]'
        self.mock_cache_client.return_value = self.mock_redis
        requested_vacc_types = {"FLU", "COVID", "RSV"}

        result = self.test_authoriser.filter_permitted_vacc_types(
            self.MOCK_SUPPLIER_NAME, ApiOperationCode.SEARCH, requested_vacc_types
        )

        self.assertSetEqual(result, requested_vacc_types)
        self.mock_redis.hget.assert_called_once_with("supplier_permissions", self.MOCK_SUPPLIER_NAME)
        self.assertNotEqual(id(requested_vacc_types), id(result))

    def test_filter_permitted_vacc_types_removes_any_vacc_types_that_the_supplier_cannot_interact_with(
        self,
    ):
        """Filter permitted vacc types method will filter out any vaccination types that the user cannot interact
        with"""
        self.mock_redis.hget.return_value = '["COVID.RS", "FLU.CRUDS", "RSV.R"]'
        self.mock_cache_client.return_value = self.mock_redis

        result = self.test_authoriser.filter_permitted_vacc_types(
            self.MOCK_SUPPLIER_NAME, ApiOperationCode.SEARCH, {"FLU", "COVID", "RSV"}
        )

        self.assertSetEqual(result, {"FLU", "COVID"})
        self.mock_redis.hget.assert_called_once_with("supplier_permissions", self.MOCK_SUPPLIER_NAME)
