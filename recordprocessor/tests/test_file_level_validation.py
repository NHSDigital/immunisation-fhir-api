"""Tests for file level validation functions"""

import unittest
from unittest.mock import patch

# If mock_s3 is not imported here then tests in other files fail when running 'make test'. It is not clear why this is.
from moto import mock_s3  # noqa: F401
from tests.utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import convert_string_to_dict_reader
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import MockFileDetails, ValidMockFileContent
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import MOCK_ENVIRONMENT_DICT

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from errors import NoOperationPermissions, InvalidHeaders
    from file_level_validation import validate_content_headers, get_permitted_operations


test_file = MockFileDetails.rsv_emis


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestFileLevelValidation(unittest.TestCase):
    """Tests for the file level validation functions"""

    def test_validate_content_headers(self):
        "Tests that validate_content_headers returns True for an exact header match and False otherwise"

        # Case: Valid file content
        # validate_content_headers takes a csv dict reader as it's input
        test_data = convert_string_to_dict_reader(ValidMockFileContent.with_new_and_update)
        self.assertIsNone(validate_content_headers(test_data))

        # Case: Invalid file content
        invalid_file_contents = [
            ValidMockFileContent.with_new_and_update.replace("SITE_CODE", "SITE_COVE"),  # Misspelled header
            ValidMockFileContent.with_new_and_update.replace("SITE_CODE|", ""),  # Missing header
            ValidMockFileContent.with_new_and_update.replace("PERSON_DOB|", "PERSON_DOB|EXTRA_HEADER|"),  # Extra header
        ]

        for invalid_file_content in invalid_file_contents:
            with self.subTest():
                # validate_content_headers takes a csv dict reader as it's input
                test_data = convert_string_to_dict_reader(invalid_file_content)
                with self.assertRaises(InvalidHeaders):
                    validate_content_headers(test_data)

    def test_get_permitted_operations(self):
        # Set up test file content. Note that ValidFileContent has action flags in lower case

        # Case: Supplier has permissions to perform at least one of the requested operations
        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions, file_content, expected_output)
        test_cases = [
            # FLU, full permissions, lowercase action flags
            ("FLU", ["FLU.CRUD"], {"CREATE", "UPDATE", "DELETE"}),
            # FLU, partial permissions, uppercase action flags
            ("FLU", ["FLU.C"], {"CREATE"}),
            # FLU, full permissions, mixed case action flags
            ("FLU", ["FLU.CRUD"], {"CREATE", "UPDATE", "DELETE"}),
            # FLU, partial permissions (create)
            ("FLU", ["FLU.D", "FLU.C"], {"CREATE", "DELETE"}),
            # FLU, partial permissions (update)
            ("FLU", ["FLU.U"], {"UPDATE"}),
            # FLU, partial permissions (delete)
            ("FLU", ["FLU.D"], {"DELETE"}),
            # COVID19, full permissions
            ("COVID19", ["COVID19.CRUD"], {"CREATE", "UPDATE", "DELETE"}),
            # COVID19, partial permissions
            ("COVID19", ["COVID19.U"], {"UPDATE"}),
            # RSV, full permissions
            ("RSV", ["RSV.CRUD"], {"CREATE", "UPDATE", "DELETE"}),
            # RSV, partial permissions
            ("RSV", ["RSV.U"], {"UPDATE"}),
            # RSV, full permissions, mixed case action flags
            ("RSV", ["RSV.CRUD"], {"CREATE", "UPDATE", "DELETE"}),
        ]

        for vaccine_type, vaccine_permissions, expected_output in test_cases:
            with self.subTest(f"Vaccine_type {vaccine_type} - permissions {vaccine_permissions}"):
                self.assertEqual(
                    get_permitted_operations("TEST_SUPPLIER", vaccine_type, vaccine_permissions),
                    expected_output,
                )

        # Case: Supplier has no permissions to perform any of the requested operations
        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions, file_content)
        invalid_cases = [
            # COVID19, no permissions
            ("COVID19", ["FLU.CRUDS", "RSV.CUD"]),
            # RSV, no valid permissions
            ("RSV", ["FLU.C", "RSV.XYZ"]),
        ]

        for vaccine_type, vaccine_permissions in invalid_cases:
            with self.subTest():
                with self.assertRaises(NoOperationPermissions):
                    get_permitted_operations("TEST_SUPPLIER", vaccine_type, vaccine_permissions)


if __name__ == "__main__":
    unittest.main()
