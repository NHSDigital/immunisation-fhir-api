"""Tests for file_key_validation functions"""

from unittest import TestCase
from unittest.mock import Mock, patch

from utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT
from utils_for_tests.utils_for_filenameprocessor_tests import (
    MOCK_ODS_CODE_TO_SUPPLIER,
    create_mock_hget,
)
from utils_for_tests.values_for_tests import MockFileDetails

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from file_validation import (
        is_file_in_directory_root,
        is_valid_datetime,
        split_file_key,
        validate_batch_file_key,
        validate_extended_attributes_file_key,
    )
    from models.errors import InvalidFileKeyError

VALID_FLU_EMIS_FILE_KEY = MockFileDetails.emis_flu.file_key
VALID_RSV_RAVS_FILE_KEY = MockFileDetails.ravs_rsv_1.file_key


@patch("elasticache.get_redis_client")
class TestFileKeyValidation(TestCase):
    """Tests for file_key_validation functions"""

    def test_is_file_in_directory_root(self, _):
        test_cases = [
            ("test_file.csv", True),
            ("archive/test_file.csv", False),
            ("processing/test_file.csv", False),
            ("lots/of/directories/init.py", False),
        ]

        for test_file_key, expected in test_cases:
            with self.subTest():
                self.assertEqual(is_file_in_directory_root(test_file_key), expected)

    def test_is_valid_datetime(self, _):
        """Tests that is_valid_datetime returns True for valid datetimes, and false otherwise"""
        # Test case tuples are structured as (date_time_string, expected_result)
        test_cases = [
            ("20200101T12345600", True),  # Valid datetime string with timezone
            ("20200101T123456", True),  # Valid datetime string without timezone
            (
                "20200101T123456extracharacters",
                True,
            ),  # Valid datetime string with additional characters
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

    def test_validate_batch_file_key(self, mock_get_redis_client):
        """Tests that file_key_validation returns True if all elements pass validation, and False otherwise"""
        # Test case tuples are structured as (file_key, expected_result)
        test_cases_for_success_scenarios = [
            # Valid FLU/ EMIS file key (mixed case)
            (VALID_FLU_EMIS_FILE_KEY, "YGM41", ("FLU", "EMIS")),
            # Valid FLU/ EMIS (all lowercase)
            (VALID_FLU_EMIS_FILE_KEY.lower(), "YGM41", ("FLU", "EMIS")),
            # Valid FLU/ EMIS (all uppercase)
            (VALID_FLU_EMIS_FILE_KEY.upper(), "YGM41", ("FLU", "EMIS")),
            # Valid RSV/ RAVS file key
            (VALID_RSV_RAVS_FILE_KEY, "X8E5B", ("RSV", "RAVS")),
            # VED-763 - Some suppliers may include ODS code at end of file for uniqueness
            (
                "RSV_Vaccinations_v5_X8E5B_20000101T00000001_ODS123.csv",
                "X8E5B",
                ("RSV", "RAVS"),
            ),
        ]

        for file_key, ods_code, expected_result in test_cases_for_success_scenarios:
            with self.subTest(f"SubTest for file key: {file_key}"):
                mock_redis = Mock()
                mock_redis.hget.side_effect = create_mock_hget(MOCK_ODS_CODE_TO_SUPPLIER, {})
                mock_redis.hkeys.return_value = ["FLU", "RSV"]
                mock_get_redis_client.return_value = mock_redis

                self.assertEqual(validate_batch_file_key(file_key), expected_result)
                mock_redis.hkeys.assert_called_with("vacc_to_diseases")
                mock_redis.hget.assert_called_with("ods_code_to_supplier", ods_code)

    def test_split_file_key(self, _):
        """Tests that split_file_key splits the file key into parts correctly"""
        test_cases = [
            (
                "FLU_Vaccinations_V5_YGM41_20000101T00000001.csv",
                (["FLU", "VACCINATIONS", "V5", "YGM41", "20000101T00000001"], "CSV"),
            ),
            (
                "Vaccination_Extended_Attributes_V1_5_X8E5B_20000101T00000001.csv",
                (["VACCINATION", "EXTENDED", "ATTRIBUTES", "V1", "5", "X8E5B", "20000101T00000001"], "CSV"),
            ),
        ]

        for file_key, expected in test_cases:
            with self.subTest(f"SubTest for file key: {file_key}"):
                self.assertEqual(split_file_key(file_key), expected)

    def test_validate_extended_attributes_file_key(self, _):
        """Tests that validate_extended_attributes_file_key returns organization code and COVID vaccine type if all
        elements pass validation, and raises an exception otherwise"""
        test_cases_for_success_scenarios = [
            # Valid extended attributes file key
            (
                "Vaccination_Extended_Attributes_v1_5_X8E5B_20000101T00000001.csv",
                "X8E5B_COVID",
            ),
            # Valid extended attributes file key with different organization code
            (
                "Vaccination_Extended_Attributes_v1_5_YGM41_20221231T23595999.csv",
                "YGM41_COVID",
            ),
        ]

        for file_key, expected_result in test_cases_for_success_scenarios:
            with self.subTest(f"SubTest for file key: {file_key}"):
                self.assertEqual(
                    validate_extended_attributes_file_key(file_key),
                    expected_result,
                )

    def test_validate_file_key_false(self, mock_get_redis_client):
        """Tests that file_key_validation returns False if elements do not pass validation"""
        invalid_file_key_error_message = "Initial file validation failed: invalid file key"
        test_cases_for_failure_scenarios = [
            # File key with additional '_'
            (
                VALID_FLU_EMIS_FILE_KEY[:2] + "_" + VALID_FLU_EMIS_FILE_KEY[2:],
                invalid_file_key_error_message,
            ),
            (
                VALID_FLU_EMIS_FILE_KEY.replace("FLU", "Flue"),
                invalid_file_key_error_message,
            ),
            # File key with missing vaccine type
            (
                VALID_FLU_EMIS_FILE_KEY.replace("FLU", ""),
                invalid_file_key_error_message,
            ),
            # File key with invalid vaccinations element
            (
                VALID_FLU_EMIS_FILE_KEY.replace("Vaccinations", "Vaccination"),
                invalid_file_key_error_message,
            ),
            # File key with missing vaccinations element
            (
                VALID_FLU_EMIS_FILE_KEY.replace("Vaccinations", ""),
                invalid_file_key_error_message,
            ),
            # File key with invalid version
            (
                VALID_FLU_EMIS_FILE_KEY.replace("v5", "v4"),
                invalid_file_key_error_message,
            ),
            # File key with missing version
            (VALID_FLU_EMIS_FILE_KEY.replace("v5", ""), invalid_file_key_error_message),
            # File key with invalid ODS code
            (
                VALID_FLU_EMIS_FILE_KEY.replace("YGM41", "YGAM"),
                invalid_file_key_error_message,
            ),
            # File key with missing ODS code
            (
                VALID_FLU_EMIS_FILE_KEY.replace("YGM41", ""),
                invalid_file_key_error_message,
            ),
            # File key with invalid timestamp
            (
                VALID_FLU_EMIS_FILE_KEY.replace("20000101T00000001", "20200132T12345600"),
                invalid_file_key_error_message,
            ),
            # File key with missing timestamp
            (
                VALID_FLU_EMIS_FILE_KEY.replace("20000101T00000001", ""),
                invalid_file_key_error_message,
            ),
            # File key with incorrect extension
            (
                VALID_FLU_EMIS_FILE_KEY.replace(".csv", ".xlsx"),
                invalid_file_key_error_message,
            ),
            # File key with ODS code but missing _ in the initial part of file key
            (
                "MMR_Vaccinations_v5_DPSFULL20250910T11225000_test.csv",
                invalid_file_key_error_message,
            ),
        ]

        for file_key, expected_result in test_cases_for_failure_scenarios:
            with self.subTest(f"SubTest for file key: {file_key}"):
                mock_redis = Mock()
                mock_redis.hget.side_effect = create_mock_hget(MOCK_ODS_CODE_TO_SUPPLIER, {})
                mock_redis.hkeys.return_value = ["FLU", "RSV"]
                mock_get_redis_client.return_value = mock_redis

                with self.assertRaises(InvalidFileKeyError) as context:
                    validate_batch_file_key(file_key)
                self.assertEqual(str(context.exception), expected_result)
                mock_redis.hkeys.assert_called_with("vacc_to_diseases")

    def test_validate_file_key_invalid(self, mock_get_redis_client):
        """Tests that file_key_validation returns False if the file key is invalid"""
        key_format_error_message = "Initial file validation failed: invalid file key format"
        missing_file_extension_error_message = "Initial file validation failed: missing file extension"
        test_cases_for_failure_scenarios = [
            # File key with no '.'
            (
                VALID_FLU_EMIS_FILE_KEY.replace(".", ""),
                missing_file_extension_error_message,
            ),
            # File key with additional '.'
            (
                VALID_FLU_EMIS_FILE_KEY[:2] + "." + VALID_FLU_EMIS_FILE_KEY[2:],
                key_format_error_message,
            ),
            # File key with missing '_'
            (VALID_FLU_EMIS_FILE_KEY.replace("_", "", 1), key_format_error_message),
            # File key with missing '_'
            (VALID_FLU_EMIS_FILE_KEY.replace("_", ""), key_format_error_message),
            # File key with missing extension
            (
                VALID_FLU_EMIS_FILE_KEY.replace(".csv", ""),
                missing_file_extension_error_message,
            ),
        ]

        for file_key, expected_result in test_cases_for_failure_scenarios:
            with self.subTest(f"SubTest for file key: {file_key}"):
                mock_redis = Mock()
                mock_redis.hget.side_effect = create_mock_hget(MOCK_ODS_CODE_TO_SUPPLIER, {})
                mock_redis.hkeys.return_value = ["FLU", "RSV"]
                mock_get_redis_client.return_value = mock_redis

                with self.assertRaises(InvalidFileKeyError) as context:
                    validate_batch_file_key(file_key)
                self.assertEqual(str(context.exception), expected_result)
                mock_redis.hkeys.assert_not_called()
