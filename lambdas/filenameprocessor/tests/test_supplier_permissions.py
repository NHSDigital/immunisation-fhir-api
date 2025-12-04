"""Tests for supplier_permissions functions"""

from unittest import TestCase
from unittest.mock import patch

from utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from models.errors import VaccineTypePermissionsError
    from supplier_permissions import (
        validate_permissions_for_extended_attributes_files,
        validate_vaccine_type_permissions,
    )


class TestSupplierPermissions(TestCase):
    """Tests for validate_vaccine_type_permissions function and its helper functions"""

    def test_validate_vaccine_type_permissions(self):
        """
        Tests that validate_vaccine_type_permissions returns True if supplier has permissions
        for the requested vaccine type and False otherwise
        """
        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions)
        success_test_cases = [
            ("FLU", ["COVID.C", "FLU.CRUDS"]),  # Full permissions for flu
            ("FLU", ["FLU.C"]),  # Create permissions for flu
            ("FLU", ["FLU.U"]),  # Update permissions for flu
            ("FLU", ["FLU.D"]),  # Delete permissions for flu
            ("COVID", ["COVID.CRUDS", "FLU.CRUDS"]),  # Full permissions for COVID
            ("COVID", ["COVID.C", "FLU.CRUDS"]),  # Create permissions for COVID
            ("RSV", ["FLU.C", "RSV.CRUDS"]),  # Full permissions for rsv
            ("RSV", ["RSV.C"]),  # Create permissions for rsv
            ("RSV", ["RSV.U"]),  # Update permissions for rsv
            ("RSV", ["RSV.D"]),  # Delete permissions for rsv
        ]

        for vaccine_type, vaccine_permissions in success_test_cases:
            with self.subTest():
                with patch(
                    "supplier_permissions.get_supplier_permissions_from_cache",
                    return_value=vaccine_permissions,
                ):
                    self.assertEqual(
                        validate_vaccine_type_permissions(vaccine_type, "TEST_SUPPLIER"),
                        vaccine_permissions,
                    )

        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions)
        failure_test_cases = [
            ("FLU", ["COVID.CRUDS"]),  # No permissions for flu
            ("COVID", ["FLU.C"]),  # No permissions for COVID
            ("RSV", ["COVID.CRUDS"]),  # No permissions for rsv
        ]

        for vaccine_type, vaccine_permissions in failure_test_cases:
            with self.subTest():
                with patch(
                    "supplier_permissions.get_supplier_permissions_from_cache",
                    return_value=vaccine_permissions,
                ):
                    with self.assertRaises(VaccineTypePermissionsError) as context:
                        validate_vaccine_type_permissions(vaccine_type, "TEST_SUPPLIER")
                self.assertEqual(
                    str(context.exception),
                    f"Initial file validation failed: TEST_SUPPLIER does not have permissions for {vaccine_type}",
                )

    def test_validate_permissions_for_extended_attributes_files_success(self):
        """Supplier with COVID CUD permissions should be accepted and identifier returned."""
        with patch(
            "supplier_permissions.get_supplier_permissions_from_cache",
            return_value=["COVID.CUDS", "FLU.CRUDS"],
        ):
            result = validate_permissions_for_extended_attributes_files("COVID", "X8E5B")
            self.assertEqual(result, "X8E5B_COVID")

    def test_validate_permissions_for_extended_attributes_files_fail_no_covid(self):
        """Supplier without any COVID permissions should raise VaccineTypePermissionsError."""
        with patch(
            "supplier_permissions.get_supplier_permissions_from_cache",
            return_value=["FLU.CRUDS"],
        ):
            with self.assertRaises(VaccineTypePermissionsError) as context:
                validate_permissions_for_extended_attributes_files("COVID", "X8E5B")
        self.assertEqual(
            str(context.exception),
            "Initial file validation failed: X8E5B does not have permissions for COVID",
        )

    def test_validate_permissions_for_extended_attributes_files_fail_partial_ops(self):
        """Supplier with only partial COVID permissions (e.g., C only) should raise error as CUD required."""
        # Note: Implementation checks only the first matching COVID entry's operation string.
        # Therefore, entries like COVID.CRUD (which includes C, U, D letters) will pass.
        # The following cases should fail because the first COVID entry lacks at least one of C/U/D.
        partial_permission_cases = [
            ["COVID.C"],
            ["COVID.U"],
            ["COVID.D"],
            ["COVID.CU"],
            ["COVID.UD"],
            ["COVID.CD"],
            ["COVID.S"],  # status only
        ]

        for permissions in partial_permission_cases:
            with self.subTest(permissions=permissions):
                with patch(
                    "supplier_permissions.get_supplier_permissions_from_cache",
                    return_value=permissions,
                ):
                    with self.assertRaises(VaccineTypePermissionsError) as context:
                        validate_permissions_for_extended_attributes_files("COVID", "X8E5B")
                self.assertEqual(
                    str(context.exception),
                    "Initial file validation failed: X8E5B does not have permissions for COVID",
                )

    def test_validate_permissions_for_extended_attributes_files_multiple_entries(self):
        """Multiple COVID permission entries should pass only if the first matching COVID entry contains CUD."""
        # Case: First entry has CUDS -> success
        with patch(
            "supplier_permissions.get_supplier_permissions_from_cache",
            return_value=["COVID.CUDS", "COVID.C"],
        ):
            result = validate_permissions_for_extended_attributes_files("COVID", "RAVS")
            self.assertEqual(result, "RAVS_COVID")

        # Case: First entry lacks CUD (even if later one has CUDS) -> fail
        with patch(
            "supplier_permissions.get_supplier_permissions_from_cache",
            return_value=["COVID.C", "COVID.CUDS"],
        ):
            with self.assertRaises(VaccineTypePermissionsError) as context:
                validate_permissions_for_extended_attributes_files("COVID", "RAVS")
        self.assertEqual(
            str(context.exception),
            "Initial file validation failed: RAVS does not have permissions for COVID",
        )

    def test_validate_permissions_for_extended_attributes_files_crud_passes(self):
        """COVID.CRUD contains C, U, D letters and should be accepted by the current implementation."""
        with patch(
            "supplier_permissions.get_supplier_permissions_from_cache",
            return_value=["COVID.CRUD"],
        ):
            result = validate_permissions_for_extended_attributes_files("COVID", "X8E5B")
            self.assertEqual(result, "X8E5B_COVID")
