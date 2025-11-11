import unittest
from unittest.mock import patch

import boto3
from moto import mock_aws

from common.utils import move_file


@mock_aws
class TestUtils(unittest.TestCase):
    def setUp(self):
        self.s3_client = boto3.client("s3", region_name="eu-west-2")

        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        self.logger_info_patcher.stop()

    def test_move_file(self):
        """VED-167 test that the file has been moved to the appropriate location"""
        bucket_name = "move-bucket"
        file_key = "src/move_file_test.csv"
        dest_key = "dest/move_file_test.csv"
        self.s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        self.s3_client.put_object(Bucket=bucket_name, Key=file_key, Body="dummy content")
        move_file(bucket_name, file_key, dest_key)
        # Assert the destination object exists
        response = self.s3_client.get_object(Bucket=bucket_name, Key=dest_key)
        content = response["Body"].read().decode()
        self.assertEqual(content, "dummy content")

        # Assert the source object no longer exists
        with self.assertRaises(self.s3_client.exceptions.NoSuchKey):
            self.s3_client.get_object(Bucket=bucket_name, Key=file_key)

        # Logger assertion (if logger is mocked)
        self.mock_logger_info.assert_called_with("File moved from %s to %s", file_key, dest_key)
