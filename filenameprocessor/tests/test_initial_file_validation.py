"""Tests for initial_file_validation functions"""

from unittest import TestCase
from unittest.mock import patch
import os
import json
import sys
from boto3 import client as boto3_client
from moto import mock_s3
maindir = os.path.dirname(__file__)
srcdir = '../src'
sys.path.insert(0, os.path.abspath(os.path.join(maindir, srcdir)))
from initial_file_validation import (   # noqa: E402
    is_valid_datetime,
    get_supplier_permissions,
    validate_vaccine_type_permissions,
    initial_file_validation,
)  # noqa: E402
from tests.utils_for_tests.values_for_tests import MOCK_ENVIRONMENT_DICT, VALID_FILE_CONTENT  # noqa: E402


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestInitialFileValidation(TestCase):
    """Tests for initial_file_validation functions"""

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

    @patch.dict(os.environ, {"REDIS_HOST": "localhost", "REDIS_PORT": "6379"})
    @patch("fetch_permissions.redis_client")
    def test_get_permissions_for_all_suppliers(self, mock_redis_client):
        """
        Test fetching permissions for all suppliers from Redis cache.
        """

        # Define the expected permissions JSON for all suppliers
        # Setup mock Redis response
        permissions_json = {
            "all_permissions": {
                "TEST_SUPPLIER_1": ["COVID19_FULL", "FLU_FULL", "RSV_FULL"],
                "TEST_SUPPLIER_2": ["FLU_CREATE", "FLU_DELETE", "RSV_CREATE"],
                "TEST_SUPPLIER_3": ["COVID19_CREATE", "COVID19_DELETE", "FLU_FULL"],
            }
        }
        mock_redis_client.get.return_value = json.dumps(permissions_json)

        # Test case tuples structured as (supplier, expected_result)
        test_cases = [
            ("TEST_SUPPLIER_1", ["COVID19_FULL", "FLU_FULL", "RSV_FULL"]),
            ("TEST_SUPPLIER_2", ["FLU_CREATE", "FLU_DELETE", "RSV_CREATE"]),
            ("TEST_SUPPLIER_3", ["COVID19_CREATE", "COVID19_DELETE", "FLU_FULL"]),
        ]

        # Run the subtests
        for supplier, expected_result in test_cases:
            with self.subTest(supplier=supplier):
                actual_permissions = get_supplier_permissions(supplier)
                self.assertEqual(actual_permissions, expected_result)

    def test_validate_vaccine_type_permissions(self):
        """
        Tests that validate_vaccine_type_permissions returns True if supplier has permissions
        for the requested vaccine type and False otherwise
        """
        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions, expected_result)
        test_cases = [
            ("FLU", ["COVID19_CREATE", "FLU_FULL"], True),  # Full permissions for flu
            ("FLU", ["FLU_CREATE"], True),  # Create permissions for flu
            ("FLU", ["FLU_UPDATE"], True),  # Update permissions for flu
            ("FLU", ["FLU_DELETE"], True),  # Delete permissions for flu
            ("FLU", ["COVID19_FULL"], False),  # No permissions for flu
            ("COVID19", ["COVID19_FULL", "FLU_FULL"], True),  # Full permissions for COVID19
            ("COVID19", ["COVID19_CREATE", "FLU_FULL"], True),  # Create permissions for COVID19
            ("COVID19", ["FLU_CREATE"], False),  # No permissions for COVID19
            ("RSV", ["FLU_CREATE", "RSV_FULL"], True),  # Full permissions for rsv
            ("RSV", ["RSV_CREATE"], True),  # Create permissions for rsv
            ("RSV", ["RSV_UPDATE"], True),  # Update permissions for rsv
            ("RSV", ["RSV_DELETE"], True),  # Delete permissions for rsv
            ("RSV", ["COVID19_FULL"], False),  # No permissions for rsv
        ]

        for vaccine_type, vaccine_permissions, expected_result in test_cases:
            with self.subTest():
                with patch("initial_file_validation.get_supplier_permissions", return_value=vaccine_permissions):
                    self.assertEqual(validate_vaccine_type_permissions("TEST_SUPPLIER", vaccine_type), expected_result)

    @mock_s3
    def test_initial_file_validation(self):
        """Tests that initial_file_validation returns True if all elements pass validation, and False otherwise"""
        bucket_name = "test_bucket"
        s3_client = boto3_client("s3", region_name="eu-west-2")
        s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        valid_file_key = "Flu_Vaccinations_v5_YGA_20200101T12345600.csv"
        valid_file_content = VALID_FILE_CONTENT

        # Test case tuples are structured as (file_key, file_content, expected_result)
        test_cases_for_full_permissions = [
            # Valid flu file key (mixed case)
            (valid_file_key, valid_file_content, (True, ["COVID19_FULL", "FLU_FULL"])),
            # Valid covid19 file key (mixed case)
            (valid_file_key.replace("Flu", "Covid19"), valid_file_content, (True, ["COVID19_FULL", "FLU_FULL"])),
            # Valid file key (all lowercase)
            (valid_file_key.lower(), valid_file_content, (True, ["COVID19_FULL", "FLU_FULL"])),
            # Valid file key (all uppercase)
            (valid_file_key.upper(), valid_file_content, (True, ["COVID19_FULL", "FLU_FULL"])),
            # File key with no '.'
            (valid_file_key.replace(".", ""), valid_file_content, False),
            # File key with additional '.'
            (valid_file_key[:2] + "." + valid_file_key[2:], valid_file_content, False),
            # File key with additional '_'
            (valid_file_key[:2] + "_" + valid_file_key[2:], valid_file_content, False),
            # File key with missing '_'
            (valid_file_key.replace("_", "", 1), valid_file_content, False),
            # File key with missing '_'
            (valid_file_key.replace("_", ""), valid_file_content, False),
            # File key with incorrect extension
            (valid_file_key.replace(".csv", ".dat"), valid_file_content, False),
            # File key with missing extension
            (valid_file_key.replace(".csv", ""), valid_file_content, False),
            # File key with invalid vaccine type
            (valid_file_key.replace("Flu", "Flue"), valid_file_content, False),
            # File key with missing vaccine type
            (valid_file_key.replace("Flu", ""), valid_file_content, False),
            # File key with invalid vaccinations element
            (valid_file_key.replace("Vaccinations", "Vaccination"), valid_file_content, False),
            # File key with missing vaccinations element
            (valid_file_key.replace("Vaccinations", ""), valid_file_content, False),
            # File key with invalid version
            (valid_file_key.replace("v5", "v4"), valid_file_content, False),
            # File key with missing version
            (valid_file_key.replace("v5", ""), valid_file_content, False),
            # File key with invalid ODS code
            (valid_file_key.replace("YGA", "YGAM"), valid_file_content, False),
            # File key with missing ODS code
            (valid_file_key.replace("YGA", "YGAM"), valid_file_content, False),
            # File key with invalid timestamp
            (valid_file_key.replace("20200101T12345600", "20200132T12345600"), valid_file_content, False),
            # File key with missing timestamp
            (valid_file_key.replace("20200101T12345600", ""), valid_file_content, False),
        ]

        for file_key, file_content, expected_result in test_cases_for_full_permissions:
            with self.subTest(f"SubTest for file key: {file_key}"):
                # Mock full permissions for the supplier (Note that YGA ODS code maps to the supplier 'TPP')
                with patch(
                    "initial_file_validation.get_permissions_config_json_from_cache",
                    return_value={"all_permissions": {"TPP": ["COVID19_FULL", "FLU_FULL"]}},
                ):
                    s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=file_content)
                    self.assertEqual(initial_file_validation(file_key), expected_result)

        # Test case tuples are structured as (file_key, file_content, expected_result)
        test_cases_for_partial_permissions = [
            # Has vaccine type and action flag permission
            (valid_file_key, valid_file_content, (True, ["FLU_CREATE"])),
            # Does not have vaccine type permission
            (valid_file_key.replace("Flu", "Covid19"), valid_file_content, False)
        ]

        for file_key, file_content, expected_result in test_cases_for_partial_permissions:
            with self.subTest(f"SubTest for file key: {file_key}"):
                # Mock permissions for the supplier (Note that YGA ODS code maps to the supplier 'TPP')
                with patch(
                    "initial_file_validation.get_permissions_config_json_from_cache",
                    return_value={"all_permissions": {"TPP": ["FLU_CREATE"]}},
                ):
                    s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=file_content)
                    self.assertEqual(initial_file_validation(file_key), expected_result)
