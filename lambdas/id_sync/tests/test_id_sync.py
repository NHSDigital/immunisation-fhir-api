import unittest
from unittest.mock import patch, MagicMock
from id_sync import handler


class TestIdSyncHandler(unittest.TestCase):

    def setUp(self):
        """Set up all patches and test fixtures"""
        # Patch all dependencies
        self.aws_lambda_event_patcher = patch('id_sync.AwsLambdaEvent')
        self.mock_aws_lambda_event = self.aws_lambda_event_patcher.start()

        self.process_record_patcher = patch('id_sync.process_record')
        self.mock_process_record = self.process_record_patcher.start()

        self.logger_patcher = patch('id_sync.logger')
        self.mock_logger = self.logger_patcher.start()

        # Patch the logging decorator to pass through
        self.log_decorator_patcher = patch('id_sync.logging_decorator')
        self.mock_log_decorator = self.log_decorator_patcher.start()
        self.mock_log_decorator.return_value = lambda f: f  # Pass-through decorator

        # Set up test data
        self.single_sqs_event = {
            'Records': [
                {
                    'messageId': '12345-abcde-67890',
                    'receiptHandle': 'AQEBwJnKyrHigUMZj6rYigCgxlaS3SLy0a...',
                    'body':
                        ('{"Records":[{"eventSource":"aws:s3","s3":{"bucket":{"name":"test-bucket"},'
                         '"object":{"key":"test-file.txt"}}}]}'),
                    'attributes': {
                        'ApproximateReceiveCount': '1',
                        'SentTimestamp': '1545082649183'
                        },
                    'messageAttributes': {},
                    'md5OfBody': 'e4e68fb7bd0e697a0ae8f1bb342846b3',
                    'eventSource': 'aws:sqs',
                    'eventSourceARN': 'arn:aws:sqs:us-east-1:123456789012:my-queue',
                    'awsRegion': 'us-east-1'
                }
            ]
        }

        self.multi_sqs_event = {
            'Records': [
                {
                    'messageId': 'message-1',
                    'receiptHandle': 'receipt-1',
                    'body': ('{"Records":[{"eventSource":"aws:s3","s3":{"bucket":{"name":"test-bucket"},'
                             '"object":{"key":"file1.txt"}}}]}'),
                    'attributes': {},
                    'messageAttributes': {},
                    'md5OfBody': 'md5-1',
                    'eventSource': 'aws:sqs',
                    'eventSourceARN': 'arn:aws:sqs:us-east-1:123456789012:my-queue',
                    'awsRegion': 'us-east-1'
                },
                {
                    'messageId': 'message-2',
                    'receiptHandle': 'receipt-2',
                    'body': ('{"Records":[{"eventSource":"aws:s3","s3":{"bucket":{"name":"test-bucket"},'
                             '"object":{"key":"file2.txt"}}}]}'),
                    'attributes': {},
                    'messageAttributes': {},
                    'md5OfBody': 'md5-2',
                    'eventSource': 'aws:sqs',
                    'eventSourceARN': 'arn:aws:sqs:us-east-1:123456789012:my-queue',
                    'awsRegion': 'us-east-1'
                }
            ]
        }

        self.empty_event = {'Records': []}
        self.no_records_event = {'someOtherKey': 'value'}

    def tearDown(self):
        """Stop all patches"""
        patch.stopall()

    def test_handler_success_single_record(self):
        """Test handler with single successful record"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.return_value = {
            "status": "success",
            "file_key": "test-file.txt"
        }

        # Call handler
        result = handler(self.single_sqs_event, None)

        # Assertions
        self.mock_aws_lambda_event.assert_called_once_with(self.single_sqs_event)
        self.mock_process_record.assert_called_once_with(mock_event.records[0], None)
        self.mock_logger.info.assert_any_call("Processing SQS event with %d records", 1)
        self.mock_logger.info.assert_any_call("Successfully processed all %d records", 1)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Successfully processed 1 records")
        self.assertEqual(result["file_keys"], ["test-file.txt"])

    def test_handler_success_multiple_records(self):
        """Test handler with multiple successful records"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock(), MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.side_effect = [
            {"status": "success", "file_key": "file1.txt"},
            {"status": "success", "file_key": "file2.txt"}
        ]

        # Call handler
        result = handler(self.multi_sqs_event, None)

        # Assertions
        self.assertEqual(self.mock_process_record.call_count, 2)
        self.mock_logger.info.assert_any_call("Processing SQS event with %d records", 2)
        self.mock_logger.info.assert_any_call("Successfully processed all %d records", 2)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Successfully processed 2 records")
        self.assertEqual(result["file_keys"], ["file1.txt", "file2.txt"])

    def test_handler_error_single_record(self):
        """Test handler with single failed record"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.return_value = {
            "status": "error",
            "file_key": "failed-file.txt"
        }

        # Call handler
        result = handler(self.single_sqs_event, None)

        # Assertions
        self.mock_process_record.assert_called_once_with(mock_event.records[0], None)
        self.mock_logger.info.assert_any_call("Processing SQS event with %d records", 1)
        self.mock_logger.error.assert_called_once_with("Processed %d records with %d errors", 1, 1)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Processed 1 records with 1 errors")
        self.assertEqual(result["file_keys"], ["failed-file.txt"])

    def test_handler_mixed_success_error(self):
        """Test handler with mix of successful and failed records"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock(), MagicMock(), MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.side_effect = [
            {"status": "success", "file_key": "success1.txt"},
            {"status": "error", "file_key": "error1.txt"},
            {"status": "success", "file_key": "success2.txt"}
        ]

        # Call handler
        result = handler(self.multi_sqs_event, None)

        # Assertions
        self.assertEqual(self.mock_process_record.call_count, 3)
        self.mock_logger.info.assert_any_call("Processing SQS event with %d records", 3)
        self.mock_logger.error.assert_called_once_with("Processed %d records with %d errors", 3, 1)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Processed 3 records with 1 errors")
        self.assertEqual(result["file_keys"], ["success1.txt", "error1.txt", "success2.txt"])

    def test_handler_all_records_fail(self):
        """Test handler when all records fail"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock(), MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.side_effect = [
            {"status": "error", "file_key": "error1.txt"},
            {"status": "error", "file_key": "error2.txt"}
        ]

        # Call handler
        result = handler(self.multi_sqs_event, None)

        # Assertions
        self.assertEqual(self.mock_process_record.call_count, 2)
        self.mock_logger.error.assert_called_once_with("Processed %d records with %d errors", 2, 2)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Processed 2 records with 2 errors")
        self.assertEqual(result["file_keys"], ["error1.txt", "error2.txt"])

    def test_handler_empty_records(self):
        """Test handler with empty records"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = []
        self.mock_aws_lambda_event.return_value = mock_event

        # Call handler
        result = handler(self.empty_event, None)

        # Assertions
        self.mock_aws_lambda_event.assert_called_once_with(self.empty_event)
        self.mock_logger.info.assert_called_once_with("No records found in event")
        self.mock_process_record.assert_not_called()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "No records found in event")

    def test_handler_no_records_key(self):
        """Test handler with no Records key in event"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = []
        self.mock_aws_lambda_event.return_value = mock_event

        # Call handler
        result = handler(self.no_records_event, None)

        # Assertions
        self.mock_aws_lambda_event.assert_called_once_with(self.no_records_event)
        self.mock_logger.info.assert_called_once_with("No records found in event")
        self.mock_process_record.assert_not_called()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "No records found in event")

    def test_handler_aws_lambda_event_exception(self):
        """Test handler when AwsLambdaEvent raises exception"""
        # Setup mock to raise exception
        self.mock_aws_lambda_event.side_effect = Exception("AwsLambdaEvent creation failed")

        # Call handler
        result = handler(self.single_sqs_event, None)

        # Assertions
        self.mock_aws_lambda_event.assert_called_once_with(self.single_sqs_event)
        self.mock_logger.exception.assert_called_once_with("Error processing id_sync event")
        self.mock_process_record.assert_not_called()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Error processing id_sync event")

    def test_handler_process_record_exception(self):
        """Test handler when process_record raises exception"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.side_effect = Exception("Process record failed")

        # Call handler
        result = handler(self.single_sqs_event, None)

        # Assertions
        self.mock_process_record.assert_called_once_with(mock_event.records[0], None)
        self.mock_logger.exception.assert_called_once_with("Error processing id_sync event")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Error processing id_sync event")

    def test_handler_process_record_missing_file_key(self):
        """Test handler when process_record returns incomplete data"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        # Missing file_key in response
        self.mock_process_record.return_value = {
            "status": "success"
            # Missing "file_key"
        }

        # Call handler
        result = handler(self.single_sqs_event, None)

        # Should catch KeyError and return error
        self.mock_logger.exception.assert_called_once_with("Error processing id_sync event")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Error processing id_sync event")

    def test_handler_process_record_missing_status(self):
        """Test handler when process_record returns missing status"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        # Missing status in response
        self.mock_process_record.return_value = {
            "file_key": "test-file.txt"
            # Missing "status"
        }

        # Call handler
        result = handler(self.single_sqs_event, None)

        # Should catch KeyError and return error
        self.mock_logger.exception.assert_called_once_with("Error processing id_sync event")
        self.assertEqual(result["status"], "error")

    def test_handler_file_keys_order_preserved(self):
        """Test that file_keys are returned in the same order as processed"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock(), MagicMock(), MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.side_effect = [
            {"status": "success", "file_key": "first.txt"},
            {"status": "success", "file_key": "second.txt"},
            {"status": "success", "file_key": "third.txt"}
        ]

        # Call handler
        result = handler(self.multi_sqs_event, None)

        # Verify order is preserved
        self.assertEqual(result["file_keys"], ["first.txt", "second.txt", "third.txt"])

    def test_handler_context_parameter_ignored(self):
        """Test that context parameter is properly ignored"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.return_value = {
            "status": "success",
            "file_key": "test-file.txt"
        }

        # Call handler with mock context
        mock_context = MagicMock()
        result = handler(self.single_sqs_event, mock_context)

        # Should work normally regardless of context
        self.assertEqual(result["status"], "success")

    def test_handler_error_count_tracking(self):
        """Test that error count is properly tracked"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.side_effect = [
            {"status": "success", "file_key": "success1.txt"},
            {"status": "error", "file_key": "error1.txt"},
            {"status": "error", "file_key": "error2.txt"},
            {"status": "success", "file_key": "success2.txt"}
        ]

        # Call handler
        result = handler(self.multi_sqs_event, None)

        # Assertions - should track 2 errors out of 4 records
        self.assertEqual(self.mock_process_record.call_count, 4)
        self.mock_logger.error.assert_called_once_with("Processed %d records with %d errors", 4, 2)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Processed 4 records with 2 errors")

    def test_handler_logs_correct_event_type(self):
        """Test that handler logs 'SQS event' for processing start"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.return_value = {
            "status": "success",
            "file_key": "test-file.txt"
        }

        # Call handler
        handler(self.single_sqs_event, None)

        # Check that it specifically logs "SQS event"
        self.mock_logger.info.assert_any_call("Processing SQS event with %d records", 1)


if __name__ == '__main__':
    unittest.main()
