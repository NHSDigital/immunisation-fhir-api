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
        self.get_record_count_patcher = patch("update_ack_file.get_record_count_by_message_id")
        self.mock_get_record_count = self.get_record_count_patcher.start()

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
        self.mock_get_record_count.return_value = 10

        # Act
        update_ack_file.complete_batch_file_process(
            message_id=message_id,
            supplier="queue-audit-table-supplier",
            vaccine_type="vaccine-type",
            created_at_formatted_string=mock_created_at_string,
            file_key=file_key,
        )

        # Assert: Only check audit table interactions
        self.mock_get_record_count.assert_called_once_with(message_id)
        self.mock_change_audit_status.assert_called_once_with(file_key, message_id)
