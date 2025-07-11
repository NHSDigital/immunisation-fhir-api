"""Tests for supplier_permissions functions"""

from unittest import TestCase
from unittest.mock import patch

from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from supplier_permissions import validate_vaccine_type_permissions
    from errors import VaccineTypePermissionsError


class TestSupplierPermissions(TestCase):
    """Tests for validate_vaccine_type_permissions function and its helper functions"""
    def test_validate_vaccine_type_permissions(self):
        """
        Tests that validate_vaccine_type_permissions returns True if supplier has permissions
        for the requested vaccine type and False otherwise
        """
        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions)
        success_test_cases = [
            ("FLU", ["COVID19.C", "FLU.CRUDS"]),  # Full permissions for flu
            ("FLU", ["FLU.C"]),  # Create permissions for flu
            ("FLU", ["FLU.U"]),  # Update permissions for flu
            ("FLU", ["FLU.D"]),  # Delete permissions for flu
            ("COVID19", ["COVID19.CRUDS", "FLU.CRUDS"]),  # Full permissions for COVID19
            ("COVID19", ["COVID19.C", "FLU.CRUDS"]),  # Create permissions for COVID19
            ("RSV", ["FLU.C", "RSV.CRUDS"]),  # Full permissions for rsv
            ("RSV", ["RSV.C"]),  # Create permissions for rsv
            ("RSV", ["RSV.U"]),  # Update permissions for rsv
            ("RSV", ["RSV.D"]),  # Delete permissions for rsv
        ]

        for vaccine_type, vaccine_permissions in success_test_cases:
            with self.subTest():
                with patch("supplier_permissions.get_supplier_permissions_from_cache", return_value=vaccine_permissions):
                    self.assertEqual(
                        validate_vaccine_type_permissions(vaccine_type, "TEST_SUPPLIER"), vaccine_permissions
                    )

        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions)
        failure_test_cases = [
            ("FLU", ["COVID19.CRUDS"]),  # No permissions for flu
            ("COVID19", ["FLU.C"]),  # No permissions for COVID19
            ("RSV", ["COVID19.CRUDS"]),  # No permissions for rsv
        ]

        for vaccine_type, vaccine_permissions in failure_test_cases:
            with self.subTest():
                with patch("supplier_permissions.get_supplier_permissions_from_cache", return_value=vaccine_permissions):
                    with self.assertRaises(VaccineTypePermissionsError) as context:
                        validate_vaccine_type_permissions(vaccine_type, "TEST_SUPPLIER")
                self.assertEqual(
                    str(context.exception),
                    f"Initial file validation failed: TEST_SUPPLIER does not have permissions for {vaccine_type}",
                )
