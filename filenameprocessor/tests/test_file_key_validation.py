"""Tests for file_key_validation functions"""

from unittest import TestCase
from unittest.mock import patch

from tests.utils_for_tests.values_for_tests import MockFileDetails
from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from file_key_validation import is_valid_datetime, validate_file_key
    from errors import InvalidFileKeyError

VALID_FLU_EMIS_FILE_KEY = MockFileDetails.emis_flu.file_key
VALID_RSV_RAVS_FILE_KEY = MockFileDetails.ravs_rsv_1.file_key


class TestFileKeyValidation(TestCase):
    """Tests for file_key_validation functions"""

    def test_is_valid_datetime(self):
        "Tests that is_valid_datetime returns True for valid datetimes, and false otherwise"
        # Test case tuples are stuctured as (date_time_string, expected_result)
        test_cases = [
            ("20200101T12345600", True),  # Valid datetime string with timezone
            ("20200101T123456", True),  # Valid datetime string without timezone
            ("20200101T123456extracharacters", True),  # Valid datetime string with additional characters
            ("20201301T12345600", False),  # Invalid month
            ("20200100T12345600", False),  # Invalid day
            ("20200230T12345600", False),  # Invalid combination of month and day
            ("20200101T24345600", False),  # Invalid hours
            ("20200101T12605600", False),  # Invalid minutes
            ("20200101T12346000", False),  # Invalid seconds
            ("2020010112345600", False),  # Invalid missing the 'T'
            ("20200101T12345", False),  # Invalid string too short
        ]

        for date_time_string, expected_result in test_cases:
            with self.subTest():
                self.assertEqual(is_valid_datetime(date_time_string), expected_result)

    def test_validate_file_key(self):
        """Tests that file_key_validation returns True if all elements pass validation, and False otherwise"""
        # Test case tuples are structured as (file_key, expected_result)
        test_cases_for_success_scenarios = [
            # Valid FLU/ EMIS file key (mixed case)
            (VALID_FLU_EMIS_FILE_KEY, ("FLU", "EMIS")),
            # Valid FLU/ EMIS (all lowercase)
            (VALID_FLU_EMIS_FILE_KEY.lower(), ("FLU", "EMIS")),
            # Valid FLU/ EMIS (all uppercase)
            (VALID_FLU_EMIS_FILE_KEY.upper(), ("FLU", "EMIS")),
            # Valid RSV/ RAVS file key
            (VALID_RSV_RAVS_FILE_KEY, ("RSV", "RAVS")),
        ]

        for file_key, expected_result in test_cases_for_success_scenarios:
            with self.subTest(f"SubTest for file key: {file_key}"):
                self.assertEqual(validate_file_key(file_key), expected_result)

        key_format_error_message = "Initial file validation failed: invalid file key format"
        invalid_file_key_error_message = "Initial file validation failed: invalid file key"
        test_cases_for_failure_scenarios = [
            # File key with no '.'
            (VALID_FLU_EMIS_FILE_KEY.replace(".", ""), key_format_error_message),
            # File key with additional '.'
            (VALID_FLU_EMIS_FILE_KEY[:2] + "." + VALID_FLU_EMIS_FILE_KEY[2:], key_format_error_message),
            # File key with additional '_'
            (VALID_FLU_EMIS_FILE_KEY[:2] + "_" + VALID_FLU_EMIS_FILE_KEY[2:], key_format_error_message),
            # File key with missing '_'
            (VALID_FLU_EMIS_FILE_KEY.replace("_", "", 1), key_format_error_message),
            # File key with missing '_'
            (VALID_FLU_EMIS_FILE_KEY.replace("_", ""), key_format_error_message),
            # File key with missing extension
            (VALID_FLU_EMIS_FILE_KEY.replace(".csv", ""), key_format_error_message),
            # File key with invalid vaccine type
            (VALID_FLU_EMIS_FILE_KEY.replace("FLU", "Flue"), invalid_file_key_error_message),
            # File key with missing vaccine type
            (VALID_FLU_EMIS_FILE_KEY.replace("FLU", ""), invalid_file_key_error_message),
            # File key with invalid vaccinations element
            (VALID_FLU_EMIS_FILE_KEY.replace("Vaccinations", "Vaccination"), invalid_file_key_error_message),
            # File key with missing vaccinations element
            (VALID_FLU_EMIS_FILE_KEY.replace("Vaccinations", ""), invalid_file_key_error_message),
            # File key with invalid version
            (VALID_FLU_EMIS_FILE_KEY.replace("v5", "v4"), invalid_file_key_error_message),
            # File key with missing version
            (VALID_FLU_EMIS_FILE_KEY.replace("v5", ""), invalid_file_key_error_message),
            # File key with invalid ODS code
            (VALID_FLU_EMIS_FILE_KEY.replace("YGM41", "YGAM"), invalid_file_key_error_message),
            # File key with missing ODS code
            (VALID_FLU_EMIS_FILE_KEY.replace("YGM41", ""), invalid_file_key_error_message),
            # File key with invalid timestamp
            (VALID_FLU_EMIS_FILE_KEY.replace("20000101T00000001", "20200132T12345600"), invalid_file_key_error_message),
            # File key with missing timestamp
            (VALID_FLU_EMIS_FILE_KEY.replace("20000101T00000001", ""), invalid_file_key_error_message),
            # File key with incorrect extension
            (VALID_FLU_EMIS_FILE_KEY.replace(".csv", ".dat"), invalid_file_key_error_message),
        ]

        for file_key, expected_result in test_cases_for_failure_scenarios:
            with self.subTest(f"SubTest for file key: {file_key}"):
                with self.assertRaises(InvalidFileKeyError) as context:
                    validate_file_key(file_key)
                self.assertEqual(str(context.exception), expected_result)
