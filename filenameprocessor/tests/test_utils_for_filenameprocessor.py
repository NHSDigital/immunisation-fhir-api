"""Tests for utils_for_filenameprocessor functions"""

from unittest import TestCase
from unittest.mock import patch
from datetime import datetime, timezone
from moto import mock_s3
from boto3 import client as boto3_client
from clients import REGION_NAME
from utils_for_filenameprocessor import get_created_at_formatted_string, get_csv_content_dict_reader, identify_supplier

s3_client = boto3_client("s3", region_name=REGION_NAME)


@mock_s3
class TestUtilsForFilenameprocessor(TestCase):
    """Tests for utils_for_filenameprocessor functions"""

    def test_get_created_at_formatted_string(self):
        """Test that get_created_at_formatted_string can correctly get the created_at_formatted_string"""
        bucket_name = "test_bucket"
        file_key = "test_file_key"

        s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": REGION_NAME})
        s3_client.put_object(Bucket=bucket_name, Key=file_key)

        mock_last_modified = {"LastModified": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}
        expected_result = "20240101T12000000"

        with patch("utils_for_filenameprocessor.s3_client.get_object", return_value=mock_last_modified):
            created_at_formatted_string = get_created_at_formatted_string(bucket_name, file_key)

        self.assertEqual(created_at_formatted_string, expected_result)

    def test_get_csv_content_dict_reader(self):
        """Test that get_csv_content_dict_reader can download and correctly read the data file"""
        bucket_name = "test_bucket"
        file_key = "test_file_key"
        file_content = "HEADER1|HEADER2\nvalue1|value2"

        s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": REGION_NAME})
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=file_content)

        csv_content_dict_reader = get_csv_content_dict_reader(bucket_name, file_key)

        for row in csv_content_dict_reader:
            self.assertEqual(row.get("HEADER1"), "value1")
            self.assertEqual(row.get("HEADER2"), "value2")

    def test_identify_supplier(self):
        """Test that identify_supplier correctly identifies supplier using ods_to_supplier_mappings"""
        # Each test case tuple has the structure (ods_code, expected_result)
        test_cases = (
            ("YGM41", "EMIS"),
            ("8J1100001", "PINNACLE"),
            ("8HK48", "SONAR"),
            ("YGA", "TPP"),
            ("0DE", "AGEM-NIVS"),
            ("0DF", "NIMS"),
            ("8HA94", "EVA"),
            ("X26", "RAVS"),
            ("YGMYH", "MEDICAL_DIRECTOR"),
            ("W00", "WELSH_DA_1"),
            ("W000", "WELSH_DA_2"),
            ("ZT001", "NORTHERN_IRELAND_DA"),
            ("YA7", "SCOTLAND_DA"),
            ("N2N9I", "COVID19_VACCINE_RESOLUTION_SERVICEDESK"),
            ("YGJ", "EMIS"),
            ("DPSREDUCED", "DPSREDUCED"),
            ("DPSFULL", "DPSFULL"),
            ("NOT_A_VALID_ODS_CODE", ""),  # Should default to empty string if ods code isn't in the mappings
        )

        for ods_code, expected_result in test_cases:
            with self.subTest(f"SubTest for ODS code: {ods_code}"):
                self.assertEqual(identify_supplier(ods_code), expected_result)
