from unittest import TestCase
from unittest.mock import patch
import json
import fakeredis

from tests.utils_for_tests.utils_for_filenameprocessor_tests import generate_permissions_config_content
from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

# Patch environment before import
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from supplier_permissions import (
        get_supplier_permissions,
        get_permissions_config_json_from_cache,
        validate_vaccine_type_permissions,
    )
    from errors import VaccineTypePermissionsError


class TestSupplierPermissions(TestCase):
    """Tests for supplier permissions logic now directly backed by Redis"""

    def setUp(self):
        self.redis_patch = patch("supplier_permissions.redis_client", fakeredis.FakeStrictRedis())
        self.mock_redis = self.redis_patch.start()

    def tearDown(self):
        self.redis_patch.stop()

    def test_get_supplier_permissions(self):
        """Test fetching supplier permissions from Redis"""
        mock_permissions = {
            "TEST_SUPPLIER_1": ["COVID19_FULL", "FLU_FULL", "RSV_FULL"],
            "TEST_SUPPLIER_2": ["FLU_CREATE", "FLU_DELETE"],
        }

        for supplier, permissions in mock_permissions.items():
            self.mock_redis.hset("permissions_config.json", supplier, json.dumps(permissions))

        for supplier, expected in mock_permissions.items():
            with self.subTest(supplier=supplier):
                self.assertEqual(get_supplier_permissions(supplier), expected)

        self.assertEqual(get_supplier_permissions("UNKNOWN_SUPPLIER"), [])

    def test_get_permissions_config_json_from_cache(self):
        """Test fetching the full permissions config from Redis"""
        all_permissions = {
            "TEST_SUPPLIER_1": ["COVID19_FULL"],
            "TEST_SUPPLIER_2": ["FLU_CREATE"],
        }
        permissions_json = generate_permissions_config_content(all_permissions)
        self.mock_redis.set("permissions_config.json", permissions_json)

        result = get_permissions_config_json_from_cache()
        self.assertEqual(result, all_permissions)

    def test_validate_vaccine_type_permissions_success(self):
        """Test vaccine type permission validation passes for valid cases"""
        valid_cases = [
            ("FLU", ["FLU_FULL"]),
            ("FLU", ["FLU_CREATE"]),
            ("COVID19", ["COVID19_DELETE"]),
            ("RSV", ["RSV_UPDATE"]),
        ]
        for vaccine_type, permissions in valid_cases:
            with self.subTest(vaccine_type=vaccine_type):
                with patch("supplier_permissions.get_supplier_permissions", return_value=permissions):
                    result = validate_vaccine_type_permissions(vaccine_type, "TEST_SUPPLIER")
                    self.assertEqual(result, permissions)

    def test_validate_vaccine_type_permissions_failure(self):
        """Test validation fails if no permission for given vaccine type"""
        invalid_cases = [
            ("FLU", ["COVID19_FULL"]),
            ("COVID19", ["RSV_CREATE"]),
            ("RSV", []),
        ]
        for vaccine_type, permissions in invalid_cases:
            with self.subTest(vaccine_type=vaccine_type):
                with patch("supplier_permissions.get_supplier_permissions", return_value=permissions):
                    with self.assertRaises(VaccineTypePermissionsError) as context:
                        validate_vaccine_type_permissions(vaccine_type, "TEST_SUPPLIER")

                    self.assertEqual(
                        str(context.exception),
                        f"Initial file validation failed: TEST_SUPPLIER does not have permissions for {vaccine_type}",
                    )