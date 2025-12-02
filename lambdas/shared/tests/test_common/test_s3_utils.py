"""Tests for common.aws_s3_utils S3 helper functions using shared resources"""

import unittest
from unittest.mock import patch

import boto3
from moto import mock_aws

from common import aws_s3_utils


@mock_aws
class TestS3UtilsShared(unittest.TestCase):
    def setUp(self):
        # Ensure environment variables used by aws_s3_utils are present
        self.env_patch = patch.dict(
            "os.environ",
            {
                "ACCOUNT_ID": "123456789012",
                "DESTINATION_BUCKET_NAME": "immunisation-batch-internal-dev-data-destinations",
            },
        )
        self.env_patch.start()

        # Region alignment with project defaults
        self.s3 = boto3.client("s3", region_name="eu-west-2")

        # Buckets for single-bucket and cross-bucket operations
        self.single_bucket = "move-bucket"
        self.source_bucket = "immunisation-batch-internal-dev-data-sources"
        self.destination_bucket = "immunisation-batch-internal-dev-data-destinations"

        for b in (self.single_bucket, self.source_bucket, self.destination_bucket):
            self.s3.create_bucket(
                Bucket=b,
                CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
            )

        # Ensure module-level variables are populated even if module was imported earlier
        aws_s3_utils.EXPECTED_BUCKET_OWNER_ACCOUNT = "123456789012"
        aws_s3_utils.DESTINATION_BUCKET_NAME = self.destination_bucket

        # Mock logger.info to verify log calls for move_file
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        # Clean up created objects and buckets
        for bucket in (self.single_bucket, self.source_bucket, self.destination_bucket):
            # Delete objects if any
            resp = self.s3.list_objects_v2(Bucket=bucket)
            for obj in resp.get("Contents", []):
                self.s3.delete_object(Bucket=bucket, Key=obj["Key"])
            # Delete bucket
            self.s3.delete_bucket(Bucket=bucket)

        self.logger_info_patcher.stop()
        self.env_patch.stop()

    def test_move_file_within_bucket(self):
        """move_file should copy and delete within the same bucket and log the move."""
        file_key = "src/move_file_test.csv"
        dest_key = "dest/move_file_test.csv"
        self.s3.put_object(Bucket=self.single_bucket, Key=file_key, Body=b"dummy content")

        aws_s3_utils.move_file(self.single_bucket, file_key, dest_key)

        # Destination has object
        response = self.s3.get_object(Bucket=self.single_bucket, Key=dest_key)
        self.assertEqual(response["Body"].read(), b"dummy content")
        # Source deleted
        with self.assertRaises(self.s3.exceptions.NoSuchKey):
            self.s3.get_object(Bucket=self.single_bucket, Key=file_key)
        # Logger called
        self.mock_logger_info.assert_called_with("File moved from %s to %s", file_key, dest_key)

    def test_move_file_outside_bucket_copies_then_deletes(self):
        """File should be copied to destination bucket under destination_key and removed from source bucket."""
        source_key = "RSV_Vaccinations_v5_X8E5B_20000101T00000001.csv"
        destination_key = f"archive/{source_key}"

        # Put an object in the source bucket
        body_content = b"dummy file content"
        self.s3.put_object(Bucket=self.source_bucket, Key=source_key, Body=body_content)

        src_obj = self.s3.get_object(Bucket=self.source_bucket, Key=source_key)
        self.assertEqual(src_obj["Body"].read(), body_content)
        with self.assertRaises(self.s3.exceptions.NoSuchKey):
            self.s3.get_object(Bucket=self.destination_bucket, Key=destination_key)

        # Execute copy across buckets
        aws_s3_utils.copy_file_to_external_bucket(
            source_bucket=self.source_bucket,
            source_key=source_key,
            destination_bucket=self.destination_bucket,
            destination_key=destination_key,
            expected_bucket_owner=aws_s3_utils.EXPECTED_BUCKET_OWNER_ACCOUNT,
            expected_source_bucket_owner=aws_s3_utils.EXPECTED_BUCKET_OWNER_ACCOUNT,
        )

        # Assert destination has the object
        dest_obj = self.s3.get_object(Bucket=self.destination_bucket, Key=destination_key)
        self.assertEqual(dest_obj["Body"].read(), body_content)

        # Assert source object was not deleted
        src_obj = self.s3.get_object(Bucket=self.source_bucket, Key=source_key)
        self.assertEqual(src_obj["Body"].read(), body_content)

        # Execute delete file
        aws_s3_utils.delete_file(
            source_bucket=self.source_bucket,
            source_key=source_key,
            expected_bucket_owner=aws_s3_utils.EXPECTED_BUCKET_OWNER_ACCOUNT,
        )

        # Assert source object was deleted
        with self.assertRaises(self.s3.exceptions.NoSuchKey):
            self.s3.get_object(Bucket=self.source_bucket, Key=source_key)
