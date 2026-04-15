"""Tests for utils_for_filenameprocessor functions"""

from datetime import UTC, datetime, timedelta
from unittest import TestCase
from unittest.mock import patch

from moto import mock_aws

from utils_for_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
)
from utils_for_tests.utils_for_filenameprocessor_tests import (
    GenericSetUp,
    GenericTearDown,
    create_boto3_clients,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from constants import AUDIT_TABLE_TTL_DAYS
    from utils_for_filenameprocessor import get_creation_and_expiry_times

s3_client = None


@mock_aws
class TestUtilsForFilenameprocessor(TestCase):
    """Tests for utils_for_filenameprocessor functions"""

    def setUp(self):
        """Set up the s3 buckets"""
        global s3_client
        (s3_client,) = create_boto3_clients("s3")
        GenericSetUp(s3_client)

    def tearDown(self):
        """Tear down the s3 buckets"""
        GenericTearDown(s3_client)

    def test_get_creation_and_expiry_times(self):
        """Test that get_creation_and_expiry_times can correctly get the created_at_formatted_string"""
        mock_last_modified_created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_last_modified_s3_response = {"LastModified": mock_last_modified_created_at}

        expected_result_created_at = "20240101T12000000"
        expected_expiry_datetime = mock_last_modified_created_at + timedelta(days=int(AUDIT_TABLE_TTL_DAYS))
        expected_result_expires_at = int(expected_expiry_datetime.timestamp())

        created_at_formatted_string, expires_at = get_creation_and_expiry_times(mock_last_modified_s3_response)

        self.assertEqual(created_at_formatted_string, expected_result_created_at)
        self.assertEqual(expires_at, expected_result_expires_at)
