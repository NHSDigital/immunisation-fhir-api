"""Tests for utils_for_filenameprocessor functions"""

from unittest import TestCase
from unittest.mock import patch
import json
from datetime import datetime, timezone
from moto import mock_s3, mock_sqs
import boto3

from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT, BucketNames
from tests.utils_for_tests.generic_setup_and_teardown import GenericSetUp, GenericTearDown

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from clients import REGION_NAME
    from utils_for_filenameprocessor import (
        get_created_at_formatted_string,
        identify_supplier,
        move_file,
        invoke_filename_lambda,
    )
    from constants import SOURCE_BUCKET_NAME, FILE_NAME_PROC_LAMBDA_NAME

@mock_sqs
@mock_s3
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestUtilsForFilenameprocessor(TestCase):
    """Tests for utils_for_filenameprocessor functions"""

    def setUp(self):
        """Set up the s3 buckets"""
        self.s3_client = boto3.client("s3", region_name=REGION_NAME)
        GenericSetUp(s3_client=self.s3_client)

    def tearDown(self):
        """Tear down the s3 buckets"""
        GenericTearDown(s3_client=self.s3_client)

    def test_get_created_at_formatted_string(self):
        """Test that get_created_at_formatted_string can correctly get the created_at_formatted_string"""
        bucket_name = BucketNames.SOURCE
        file_key = "test_file_key"

        self.s3_client.put_object(Bucket=bucket_name, Key=file_key)

        mock_last_modified = {"LastModified": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}
        expected_result = "20240101T12000000"

        with patch.object(self.s3_client, "get_object", return_value=mock_last_modified):
            with patch("utils_for_filenameprocessor.s3_client", self.s3_client):
                created_at_formatted_string = get_created_at_formatted_string(bucket_name, file_key)

        self.assertEqual(created_at_formatted_string, expected_result)

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

    def test_move_file(self):
        """Tests that move_file correctly moves a file from one location to another within a single S3 bucket"""
        source_file_key = "test_file_key"
        destination_file_key = "destination/test_file_key"
        source_file_content = "test_content"
        self.s3_client.put_object(Bucket=BucketNames.SOURCE, Key=source_file_key, Body=source_file_content)

        move_file(self.s3_client, BucketNames.SOURCE, source_file_key, destination_file_key)

        keys_of_objects_in_bucket = [
            obj["Key"] for obj in self.s3_client.list_objects_v2(Bucket=BucketNames.SOURCE).get("Contents")
        ]
        self.assertNotIn(source_file_key, keys_of_objects_in_bucket)
        self.assertIn(destination_file_key, keys_of_objects_in_bucket)
        destination_file_content = self.s3_client.get_object(Bucket=BucketNames.SOURCE, Key=destination_file_key)
        self.assertEqual(destination_file_content["Body"].read().decode("utf-8"), source_file_content)

    
