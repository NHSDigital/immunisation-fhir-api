import unittest
from unittest.mock import patch, MagicMock


with patch('common.log_decorator.logging_decorator') as mock_decorator:
    mock_decorator.return_value = lambda f: f  # Pass-through decorator
    from id_sync import handler
    from exceptions.id_sync_exception import IdSyncException


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
        # Set up test data
        self.single_sqs_event = {
            'Records': [
                {
                    'body': '{"source":"aws:sqs","data":"test-data"}'
                }
            ]
        }

        self.multi_sqs_event = {
            'Records': [
                {
                    'body': ('{"source":"aws:sqs","data":"a"}'),
                },
                {
                    'body': ('{"source":"aws:sqs","data":"b"}'),
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
            "nhs_number": "test-nhs-number"
        }

        # Call handler
        result = handler(self.single_sqs_event, None)

        # Assertions
        self.mock_aws_lambda_event.assert_called_once_with(self.single_sqs_event)
        self.mock_process_record.assert_called_once_with(mock_event.records[0])

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Successfully processed 1 records")
        self.assertEqual(result["nhs_numbers"], ["test-nhs-number"])

    def test_handler_success_multiple_records(self):
        """Test handler with multiple successful records"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock(), MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.side_effect = [
            {"status": "success", "nhs_number": "test-nhs-number-1"},
            {"status": "success", "nhs_number": "test-nhs-number-2"}
        ]

        # Call handler
        result = handler(self.multi_sqs_event, None)

        # Assertions
        self.assertEqual(self.mock_process_record.call_count, 2)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Successfully processed 2 records")
        self.assertEqual(result["nhs_numbers"], ["test-nhs-number-1", "test-nhs-number-2"])

    def test_handler_error_single_record(self):
        """Test handler with single failed record"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.return_value = {
            "status": "error",
            "nhs_number": "failed-nhs-number"
        }

        # Call handler
        with self.assertRaises(IdSyncException) as exception_context:
            handler(self.single_sqs_event, None)

        exception = exception_context.exception
        # Assertions
        self.mock_process_record.assert_called_once_with(mock_event.records[0])
        self.mock_logger.info.assert_any_call("id_sync processing event with %d records", 1)

        self.assertEqual(exception.message, "Processed 1 records with 1 errors")
        self.assertEqual(exception.nhs_numbers, ["failed-nhs-number"])

    def test_handler_mixed_success_error(self):
        """Test handler with mix of successful and failed records"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock(), MagicMock(), MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.side_effect = [
            {"status": "success", "nhs_number": "test-nhs-number-1"},
            {"status": "error", "nhs_number": "test-nhs-number-2"},
            {"status": "success", "nhs_number": "test-nhs-number-3"}
        ]

        # Call handler
        with self.assertRaises(IdSyncException) as exception_context:
            handler(self.multi_sqs_event, None)

        error = exception_context.exception
        # Assertions
        self.assertEqual(self.mock_process_record.call_count, 3)

        self.assertEqual(error.message, "Processed 3 records with 1 errors")
        self.assertEqual(error.nhs_numbers, ["test-nhs-number-1", "test-nhs-number-2", "test-nhs-number-3"])

    def test_handler_all_records_fail(self):
        """Test handler when all records fail"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock(), MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.side_effect = [
            {"status": "error", "nhs_number": "test-nhs-number-1"},
            {"status": "error", "nhs_number": "test-nhs-number-2"}
        ]

        # Call handler
        with self.assertRaises(IdSyncException) as exception_context:
            handler(self.multi_sqs_event, None)
        exception = exception_context.exception
        # Assertions
        self.assertEqual(self.mock_process_record.call_count, 2)

        self.assertEqual(exception.nhs_numbers, ["test-nhs-number-1", "test-nhs-number-2"])
        self.assertEqual(exception.message, "Processed 2 records with 2 errors")

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
        self.mock_process_record.assert_not_called()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "No records found in event")

    def test_handler_aws_lambda_event_exception(self):
        """Test handler when AwsLambdaEvent raises exception"""
        # Setup mock to raise exception
        self.mock_aws_lambda_event.side_effect = Exception("AwsLambdaEvent creation failed")

        # Call handler
        with self.assertRaises(IdSyncException) as exception_context:
            handler(self.single_sqs_event, None)

        result = exception_context.exception
        # Assertions
        self.mock_aws_lambda_event.assert_called_once_with(self.single_sqs_event)
        self.mock_logger.exception.assert_called_once_with("Error processing id_sync event")
        self.mock_process_record.assert_not_called()

        self.assertEqual(result.nhs_numbers, None)
        self.assertEqual(result.message, "Error processing id_sync event")

    def test_handler_process_record_exception(self):
        """Test handler when process_record raises exception"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.side_effect = Exception("Process record failed")

        # Call handler
        with self.assertRaises(IdSyncException) as exception_context:
            handler(self.single_sqs_event, None)
        exception = exception_context.exception
        # Assertions
        self.mock_process_record.assert_called_once_with(mock_event.records[0])
        self.mock_logger.exception.assert_called_once_with("Error processing id_sync event")

        self.assertEqual(exception.nhs_numbers, None)
        self.assertEqual(exception.message, "Error processing id_sync event")

    def test_handler_process_record_missing_nhs_number(self):
        """Test handler when process_record returns incomplete data"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        # Missing "nhs_number" in response
        self.mock_process_record.return_value = {
            "status": "success"
            # Missing "nhs_number"
        }

        # Call handler
        with self.assertRaises(IdSyncException) as exception_context:
            handler(self.single_sqs_event, None)

        exception = exception_context.exception

        # convert exception payload to json
        self.assertIsInstance(exception, IdSyncException)
        self.assertEqual(exception.nhs_numbers, None)
        self.assertEqual(exception.message, "Error processing id_sync event")
        self.mock_logger.exception.assert_called_once_with("Error processing id_sync event")

    def test_handler_context_parameter_ignored(self):
        """Test that context parameter is properly ignored"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.records = [MagicMock()]
        self.mock_aws_lambda_event.return_value = mock_event

        self.mock_process_record.return_value = {
            "status": "success",
            "nhs_number": "nnhs-number-01"
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

        good_num1 = "nhs-number-success1"
        good_num2 = "nhs-number-success2"
        bad_num1 = "nhs-number-error1"
        bad_num2 = "nhs-number-error2"

        self.mock_process_record.side_effect = [
            {"status": "success", "nhs_number": good_num1},
            {"status": "error", "nhs_number": bad_num1},
            {"status": "error", "nhs_number": bad_num2},
            {"status": "success", "nhs_number": good_num2}
        ]

        # Call handler
        with self.assertRaises(IdSyncException) as exception_context:
            handler(self.multi_sqs_event, None)
        exception = exception_context.exception
        # Assertions - should track 2 errors out of 4 records
        self.assertEqual(self.mock_process_record.call_count, 4)

        self.assertEqual(exception.nhs_numbers,
                         [good_num1,
                          bad_num1,
                          bad_num2,
                          good_num2])
        self.assertEqual(exception.message, "Processed 4 records with 2 errors")
