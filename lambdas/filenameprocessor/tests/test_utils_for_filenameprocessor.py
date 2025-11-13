"""Tests for utils_for_filenameprocessor functions"""

from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch

from boto3 import client as boto3_client
from moto import mock_s3

from utils_for_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
)
from utils_for_tests.utils_for_filenameprocessor_tests import (
    GenericSetUp,
    GenericTearDown,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.clients import REGION_NAME
    from constants import AUDIT_TABLE_TTL_DAYS
    from utils_for_filenameprocessor import get_creation_and_expiry_times

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
