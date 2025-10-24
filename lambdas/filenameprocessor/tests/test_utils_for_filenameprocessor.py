"""Tests for utils_for_filenameprocessor functions"""

from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch

from boto3 import client as boto3_client
from moto import mock_s3

from tests.utils_for_tests.generic_setup_and_teardown import (
    GenericSetUp,
    GenericTearDown,
)
from tests.utils_for_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    BucketNames,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.clients import REGION_NAME
    from constants import AUDIT_TABLE_TTL_DAYS
    from utils_for_filenameprocessor import get_creation_and_expiry_times, move_file

s3_client = boto3_client("s3", region_name=REGION_NAME)


@mock_s3
class TestUtilsForFilenameprocessor(TestCase):
    """Tests for utils_for_filenameprocessor functions"""

    def setUp(self):
        """Set up the s3 buckets"""
        GenericSetUp(s3_client)

    def tearDown(self):
        """Tear down the s3 buckets"""
        GenericTearDown(s3_client)

    def test_get_creation_and_expiry_times(self):
        """Test that get_creation_and_expiry_times can correctly get the created_at_formatted_string"""
        mock_last_modified_created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_last_modified_s3_response = {"LastModified": mock_last_modified_created_at}

        expected_result_created_at = "20240101T12000000"
        expected_expiry_datetime = mock_last_modified_created_at + timedelta(days=int(AUDIT_TABLE_TTL_DAYS))
        expected_result_expires_at = int(expected_expiry_datetime.timestamp())

        created_at_formatted_string, expires_at = get_creation_and_expiry_times(mock_last_modified_s3_response)

        self.assertEqual(created_at_formatted_string, expected_result_created_at)
        self.assertEqual(expires_at, expected_result_expires_at)

    def test_move_file(self):
        """Tests that move_file correctly moves a file from one location to another within a single S3 bucket"""
        source_file_key = "test_file_key"
        destination_file_key = "destination/test_file_key"
        source_file_content = "test_content"
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=source_file_key, Body=source_file_content)

        move_file(BucketNames.SOURCE, source_file_key, destination_file_key)

        keys_of_objects_in_bucket = [
            obj["Key"] for obj in s3_client.list_objects_v2(Bucket=BucketNames.SOURCE).get("Contents")
        ]
        self.assertNotIn(source_file_key, keys_of_objects_in_bucket)
        self.assertIn(destination_file_key, keys_of_objects_in_bucket)
        destination_file_content = s3_client.get_object(Bucket=BucketNames.SOURCE, Key=destination_file_key)
        self.assertEqual(destination_file_content["Body"].read().decode("utf-8"), source_file_content)
