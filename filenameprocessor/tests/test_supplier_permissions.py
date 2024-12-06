"""Tests for supplier_permissions functions"""

from unittest import TestCase
from unittest.mock import patch
from supplier_permissions import validate_vaccine_type_permissions, get_supplier_permissions
from errors import VaccineTypePermissionsError
from tests.utils_for_tests.utils_for_filenameprocessor_tests import generate_permissions_config_content


class TestSupplierPermissions(TestCase):
    """Tests for validate_vaccine_type_permissions function and its helper functions"""

    def test_get_permissions_for_all_suppliers(self):
        """Test fetching permissions for all suppliers from Redis cache."""
        # Setup mock Redis response with the following permissions
        permissions_config_content = generate_permissions_config_content(
            {
                "TEST_SUPPLIER_1": ["COVID19_FULL", "FLU_FULL", "RSV_FULL"],
                "TEST_SUPPLIER_2": ["FLU_CREATE", "FLU_DELETE", "RSV_CREATE"],
                "TEST_SUPPLIER_3": ["COVID19_CREATE", "COVID19_DELETE", "FLU_FULL"],
            }
        )

        # Test case tuples structured as (supplier, expected_result)
        test_cases = [
            ("TEST_SUPPLIER_1", ["COVID19_FULL", "FLU_FULL", "RSV_FULL"]),
            ("TEST_SUPPLIER_2", ["FLU_CREATE", "FLU_DELETE", "RSV_CREATE"]),
            ("TEST_SUPPLIER_3", ["COVID19_CREATE", "COVID19_DELETE", "FLU_FULL"]),
        ]

        # Run the subtests
        for supplier, expected_result in test_cases:
            with self.subTest(supplier=supplier):
                with patch("supplier_permissions.redis_client.get", return_value=permissions_config_content):
                    actual_permissions = get_supplier_permissions(supplier)
                    self.assertEqual(actual_permissions, expected_result)

    def test_validate_vaccine_type_permissions(self):
        """
        Tests that validate_vaccine_type_permissions returns True if supplier has permissions
        for the requested vaccine type and False otherwise
        """
        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions)
        success_test_cases = [
            ("FLU", ["COVID19_CREATE", "FLU_FULL"]),  # Full permissions for flu
            ("FLU", ["FLU_CREATE"]),  # Create permissions for flu
            ("FLU", ["FLU_UPDATE"]),  # Update permissions for flu
            ("FLU", ["FLU_DELETE"]),  # Delete permissions for flu
            ("COVID19", ["COVID19_FULL", "FLU_FULL"]),  # Full permissions for COVID19
            ("COVID19", ["COVID19_CREATE", "FLU_FULL"]),  # Create permissions for COVID19
            ("RSV", ["FLU_CREATE", "RSV_FULL"]),  # Full permissions for rsv
            ("RSV", ["RSV_CREATE"]),  # Create permissions for rsv
            ("RSV", ["RSV_UPDATE"]),  # Update permissions for rsv
            ("RSV", ["RSV_DELETE"]),  # Delete permissions for rsv
        ]

        for vaccine_type, vaccine_permissions in success_test_cases:
            with self.subTest():
                with patch("supplier_permissions.get_supplier_permissions", return_value=vaccine_permissions):
                    self.assertEqual(
                        validate_vaccine_type_permissions(vaccine_type, "TEST_SUPPLIER"), vaccine_permissions
                    )

        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions)
        failure_test_cases = [
            ("FLU", ["COVID19_FULL"]),  # No permissions for flu
            ("COVID19", ["FLU_CREATE"]),  # No permissions for COVID19
            ("RSV", ["COVID19_FULL"]),  # No permissions for rsv
        ]

        for vaccine_type, vaccine_permissions in failure_test_cases:
            with self.subTest():
                with patch("supplier_permissions.get_supplier_permissions", return_value=vaccine_permissions):
                    with self.assertRaises(VaccineTypePermissionsError) as context:
                        validate_vaccine_type_permissions(vaccine_type, "TEST_SUPPLIER")
                self.assertEqual(
                    str(context.exception),
                    f"Initial file validation failed: TEST_SUPPLIER does not have permissions for {vaccine_type}",
                )
