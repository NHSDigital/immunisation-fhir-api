"""Tests for file level validation functions"""

import unittest
from unittest.mock import patch

# If mock_s3 is not imported here then tests in other files fail when running 'make test'. It is not clear why this is.
from moto import mock_s3  # noqa: F401
from tests.utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import (
    convert_string_to_dict_reader,
)
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    MockFileDetails,
    ValidMockFileContent,
)
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    MOCK_ENVIRONMENT_DICT,
)

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from errors import NoOperationPermissions, InvalidHeaders
    from file_level_validation import (
        validate_content_headers,
        validate_action_flag_permissions,
    )


test_file = MockFileDetails.rsv_emis


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestFileLevelValidation(unittest.TestCase):
    """Tests for the file level validation functions"""

    def test_validate_content_headers(self):
        "Tests that validate_content_headers returns True for an exact header match and False otherwise"

        # Case: Valid file content
        # validate_content_headers takes a csv dict reader as it's input
        test_data = convert_string_to_dict_reader(
            ValidMockFileContent.with_new_and_update
        )
        self.assertIsNone(validate_content_headers(test_data))

        # Case: Invalid file content
        invalid_file_contents = [
            ValidMockFileContent.with_new_and_update.replace(
                "SITE_CODE", "SITE_COVE"
            ),  # Misspelled header
            ValidMockFileContent.with_new_and_update.replace(
                "SITE_CODE|", ""
            ),  # Missing header
            ValidMockFileContent.with_new_and_update.replace(
                "PERSON_DOB|", "PERSON_DOB|EXTRA_HEADER|"
            ),  # Extra header
        ]

        for invalid_file_content in invalid_file_contents:
            with self.subTest():
                # validate_content_headers takes a csv dict reader as it's input
                test_data = convert_string_to_dict_reader(invalid_file_content)
                with self.assertRaises(InvalidHeaders):
                    validate_content_headers(test_data)

    def test_validate_action_flag_permissions(self):
        """
        Tests that validate_action_flag_permissions returns True if supplier has permissions to perform at least one
        of the requested CRUD operations for the given vaccine type, and False otherwise
        """
        # Set up test file content. Note that ValidFileContent has action flags in lower case
        valid_file_content = ValidMockFileContent.with_new_and_update
        valid_content_new_and_update_lowercase = valid_file_content
        valid_content_new_and_update_uppercase = valid_file_content.replace(
            "new", "NEW"
        ).replace("update", "UPDATE")
        valid_content_new_and_update_mixedcase = valid_file_content.replace(
            "new", "New"
        ).replace("update", "uPdAte")
        valid_content_new_and_delete_lowercase = valid_file_content.replace(
            "update", "delete"
        )
        valid_content_update_and_delete_lowercase = valid_file_content.replace(
            "new", "delete"
        ).replace("update", "UPDATE")

        # Case: Supplier has permissions to perform at least one of the requested operations
        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions, file_content, expected_output)
        test_cases = [
            # FLU, full permissions, lowercase action flags
            (
                "FLU",
                ["FLU_FULL"],
                valid_content_new_and_update_lowercase,
                {"CREATE", "UPDATE", "DELETE"},
            ),
            # FLU, partial permissions, uppercase action flags
            ("FLU", ["FLU_CREATE"], valid_content_new_and_update_uppercase, {"CREATE"}),
            # FLU, full permissions, mixed case action flags
            (
                "FLU",
                ["FLU_FULL"],
                valid_content_new_and_update_mixedcase,
                {"CREATE", "UPDATE", "DELETE"},
            ),
            # FLU, partial permissions (create)
            (
                "FLU",
                ["FLU_DELETE", "FLU_CREATE"],
                valid_content_new_and_update_lowercase,
                {"CREATE", "DELETE"},
            ),
            # FLU, partial permissions (update)
            ("FLU", ["FLU_UPDATE"], valid_content_new_and_update_lowercase, {"UPDATE"}),
            # FLU, partial permissions (delete)
            ("FLU", ["FLU_DELETE"], valid_content_new_and_delete_lowercase, {"DELETE"}),
            # COVID19, full permissions
            (
                "COVID19",
                ["COVID19_FULL"],
                valid_content_new_and_delete_lowercase,
                {"CREATE", "UPDATE", "DELETE"},
            ),
            # COVID19, partial permissions
            (
                "COVID19",
                ["COVID19_UPDATE"],
                valid_content_update_and_delete_lowercase,
                {"UPDATE"},
            ),
            # RSV, full permissions
            (
                "RSV",
                ["RSV_FULL"],
                valid_content_new_and_delete_lowercase,
                {"CREATE", "UPDATE", "DELETE"},
            ),
            # RSV, partial permissions
            (
                "RSV",
                ["RSV_UPDATE"],
                valid_content_update_and_delete_lowercase,
                {"UPDATE"},
            ),
            # RSV, full permissions, mixed case action flags
            (
                "RSV",
                ["RSV_FULL"],
                valid_content_new_and_update_mixedcase,
                {"CREATE", "UPDATE", "DELETE"},
            ),
        ]

        for (
            vaccine_type,
            vaccine_permissions,
            file_content,
            expected_output,
        ) in test_cases:
            with self.subTest(
                f"Vaccine_type {vaccine_type} - permissions {vaccine_permissions}"
            ):
                self.assertEqual(
                    validate_action_flag_permissions(
                        "TEST_SUPPLIER", vaccine_type, vaccine_permissions, file_content
                    ),
                    expected_output,
                )

        # Case: Supplier has no permissions to perform any of the requested operations
        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions, file_content)
        test_cases = [
            # FLU, no permissions
            (
                "FLU",
                ["FLU_UPDATE", "COVID19_FULL"],
                valid_content_new_and_delete_lowercase,
            ),
            # COVID19, no permissions
            (
                "COVID19",
                ["FLU_CREATE", "FLU_UPDATE"],
                valid_content_update_and_delete_lowercase,
            ),
            # RSV, no permissions
            (
                "RSV",
                ["FLU_CREATE", "FLU_UPDATE"],
                valid_content_update_and_delete_lowercase,
            ),
        ]

        for vaccine_type, vaccine_permissions, file_content in test_cases:
            with self.subTest():
                with self.assertRaises(NoOperationPermissions):
                    validate_action_flag_permissions(
                        "TEST_SUPPLIER", vaccine_type, vaccine_permissions, file_content
                    )


if __name__ == "__main__":
    unittest.main()
