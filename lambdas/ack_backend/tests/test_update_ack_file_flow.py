import unittest
from unittest.mock import patch

import boto3
from moto import mock_aws

import update_ack_file


@mock_aws
class TestUpdateAckFileFlow(unittest.TestCase):
    def setUp(self):
        self.s3_client = boto3.client("s3", region_name="eu-west-2")

        self.ack_bucket_name = "my-ack-bucket"
        self.source_bucket_name = "my-source-bucket"
        self.ack_bucket_patcher = patch("update_ack_file.get_ack_bucket_name", return_value=self.ack_bucket_name)
        self.mock_get_ack_bucket_name = self.ack_bucket_patcher.start()

        self.source_bucket_patcher = patch(
            "update_ack_file.get_source_bucket_name",
            return_value=self.source_bucket_name,
        )
        self.mock_get_source_bucket_name = self.source_bucket_patcher.start()

        self.s3_client.create_bucket(
            Bucket=self.ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        self.s3_client.create_bucket(
            Bucket=self.source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        self.logger_patcher = patch("update_ack_file.logger")
        self.mock_logger = self.logger_patcher.start()

        self.change_audit_status_patcher = patch("update_ack_file.change_audit_table_status_to_processed")
        self.mock_change_audit_status = self.change_audit_status_patcher.start()

    def tearDown(self):
        self.logger_patcher.stop()
        self.change_audit_status_patcher.stop()

    def test_audit_table_updated_correctly_when_ack_process_complete(self):
        """VED-167 - Test that the audit table has been updated correctly"""
        # Setup
        message_id = "msg-audit-table"
        mock_created_at_string = "created_at_formatted_string"
        file_key = "audit_table_test.csv"
        self.s3_client.put_object(
            Bucket=self.source_bucket_name,
            Key=f"processing/{file_key}",
            Body="dummy content",
        )
        self.s3_client.put_object(
            Bucket=self.ack_bucket_name, Key=f"TempAck/audit_table_test_BusAck_{mock_created_at_string}.csv"
        )

        # Act
        update_ack_file.complete_batch_file_process(
            message_id=message_id,
            supplier="queue-audit-table-supplier",
            vaccine_type="vaccine-type",
            created_at_formatted_string=mock_created_at_string,
            file_key=file_key,
            total_ack_rows_processed=3,
        )

        # Assert: Only check audit table update
        self.mock_change_audit_status.assert_called_once_with(file_key, message_id)

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
        update_ack_file.move_file(bucket_name, file_key, dest_key)
        # Assert the destination object exists
        response = self.s3_client.get_object(Bucket=bucket_name, Key=dest_key)
        content = response["Body"].read().decode()
        self.assertEqual(content, "dummy content")

        # Assert the source object no longer exists
        with self.assertRaises(self.s3_client.exceptions.NoSuchKey):
            self.s3_client.get_object(Bucket=bucket_name, Key=file_key)

        # Logger assertion (if logger is mocked)
        self.mock_logger.info.assert_called_with("File moved from %s to %s", file_key, dest_key)
