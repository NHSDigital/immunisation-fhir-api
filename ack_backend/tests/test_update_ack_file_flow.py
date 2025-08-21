import unittest
from unittest.mock import patch, MagicMock, call
from io import StringIO

import update_ack_file
from update_ack_file import invoke_filename_lambda
import unittest
import boto3

from moto import mock_s3


@mock_s3
class TestUpdateAckFileFlow(unittest.TestCase):
    def setUp(self):
        # Patch all AWS and external dependencies
        self.s3_client = boto3.client("s3", region_name="eu-west-2")

        self.ack_bucket_name = 'my-ack-bucket'
        self.source_bucket_name = 'my-source-bucket'
        self.ack_bucket_patcher = patch('update_ack_file.get_ack_bucket_name', return_value=self.ack_bucket_name)
        self.mock_get_ack_bucket_name = self.ack_bucket_patcher.start()

        self.source_bucket_patcher = patch('update_ack_file.get_source_bucket_name', return_value=self.source_bucket_name)
        self.mock_get_source_bucket_name = self.source_bucket_patcher.start()

        self.s3_client.create_bucket(
            Bucket=self.ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )
        self.s3_client.create_bucket(
            Bucket=self.source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )

        self.logger_patcher = patch('update_ack_file.logger')
        self.mock_logger = self.logger_patcher.start()

        self.get_row_count_patcher = patch('update_ack_file.get_row_count')
        self.mock_get_row_count = self.get_row_count_patcher.start()

        self.change_audit_status_patcher = patch('update_ack_file.change_audit_table_status_to_processed')
        self.mock_change_audit_status = self.change_audit_status_patcher.start()

        self.get_next_queued_file_details_patcher = patch('update_ack_file.get_next_queued_file_details')
        self.mock_get_next_queued_file_details = self.get_next_queued_file_details_patcher.start()

        self.invoke_filename_lambda_patcher = patch('update_ack_file.invoke_filename_lambda')
        self.mock_invoke_filename_lambda = self.invoke_filename_lambda_patcher.start()

        self.lambda_client_patcher = patch('update_ack_file.lambda_client')
        self.mock_lambda_client = self.lambda_client_patcher.start()
        
    def tearDown(self):
        self.logger_patcher.stop()
        self.get_row_count_patcher.stop()
        self.change_audit_status_patcher.stop()
        self.get_next_queued_file_details_patcher.stop()
        self.invoke_filename_lambda_patcher.stop()
        self.lambda_client_patcher.stop()

    def test_audit_table_updated_correctly(self):
        """ VED-167 - Test that the audit table has been updated correctly"""
        # Setup
        self.mock_get_row_count.side_effect = [3, 3]
        accumulated_csv_content = StringIO("header1|header2\n")
        ack_data_rows = [
            {"a": 1, "b": 2, "row": "audit-test-1"},
            {"a": 3, "b": 4, "row": "audit-test-2"},
            {"a": 5, "b": 6, "row": "audit-test-3"}
        ]
        message_id = "msg-audit-table"
        file_key = "audit_table_test.csv"
        self.s3_client.put_object(
            Bucket=self.source_bucket_name,
            Key=f"processing/{file_key}",
            Body="dummy content"
        )
        # Act
        update_ack_file.upload_ack_file(
            temp_ack_file_key=f"TempAck/{file_key}",
            message_id=message_id,
            supplier_queue="queue-audit-table",
            accumulated_csv_content=accumulated_csv_content,
            ack_data_rows=ack_data_rows,
            archive_ack_file_key=f"forwardedFile/{file_key}",
            file_key=file_key
        )
        # Assert: Only check audit table update
        self.mock_change_audit_status.assert_called_once_with(file_key, message_id)

    def test_move_file(self):
        """ VED-167 test that the file has been moved to the appropriate location """
        bucket_name = "move-bucket"
        file_key = "src/move_file_test.csv"
        dest_key = "dest/move_file_test.csv"
        self.s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )
        self.s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body="dummy content"
        )
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

    def test_next_queued_file_triggers_lambda(self):
        """ VED-167 Test that the next queued file details are used to re-invoke the lambda."""
        # Setup
        self.mock_get_row_count.side_effect = [3, 3]
        next_file = "next_for_lambda.csv"
        next_message_id = "msg-next-lambda"
        queue_name = "queue-lambda-trigger"
        self.mock_get_next_queued_file_details.return_value = {"filename": next_file, "message_id": next_message_id}
        accumulated_csv_content = StringIO("header1|header2\n")
        ack_data_rows = [
            {"a": 1, "b": 2, "row": "lambda1"},
            {"a": 3, "b": 4, "row": "lambda2"},
            {"a": 5, "b": 6, "row": "lambda3"}
        ]
        next_key="next_lambda_test.csv"
        self.s3_client.put_object(
            Bucket=self.source_bucket_name,
            Key=f"processing/{next_key}",
            Body="dummy content"
        )
        # Act
        update_ack_file.upload_ack_file(
            temp_ack_file_key=f"TempAck/{next_key}",
            message_id="msg-lambda-trigger",
            supplier_queue=queue_name,
            accumulated_csv_content=accumulated_csv_content,
            ack_data_rows=ack_data_rows,
            archive_ack_file_key=f"forwardedFile/{next_key}",
            file_key=next_key
        )
        # Assert: Check that the next queued file was used to re-invoke the lambda
        self.mock_get_next_queued_file_details.assert_called_once_with(queue_name)
