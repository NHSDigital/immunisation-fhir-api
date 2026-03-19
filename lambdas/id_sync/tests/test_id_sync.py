import unittest
from unittest.mock import MagicMock, patch

with patch("common.log_decorator.logging_decorator") as mock_decorator:
    mock_decorator.return_value = lambda f: f
    from id_sync import handler


class TestIdSyncHandler(unittest.TestCase):
    def setUp(self):
        self.aws_lambda_event_patcher = patch("id_sync.AwsLambdaEvent")
        self.mock_aws_lambda_event = self.aws_lambda_event_patcher.start()

        self.process_record_patcher = patch("id_sync.process_record")
        self.mock_process_record = self.process_record_patcher.start()

        self.logger_patcher = patch("id_sync.logger")
        self.mock_logger = self.logger_patcher.start()

        self.single_sqs_event = {"Records": [{"messageId": "msg-1", "body": '{"subject":"9000000001"}'}]}
        self.multi_sqs_event = {
            "Records": [
                {"messageId": "msg-1", "body": '{"subject":"9000000001"}'},
                {"messageId": "msg-2", "body": '{"subject":"9000000002"}'},
                {"messageId": "msg-3", "body": '{"subject":"9000000003"}'},
            ]
        }
        self.empty_event = {"Records": []}
        self.no_records_event = {"someOtherKey": "value"}

    def tearDown(self):
        patch.stopall()

    def test_single_record_success(self):
        mock_event = MagicMock()
        mock_event.records = [{"messageId": "msg-1"}]
        self.mock_aws_lambda_event.return_value = mock_event
        self.mock_process_record.return_value = {"status": "success"}

        result = handler(self.single_sqs_event, None)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Successfully processed 1 records")
        self.assertNotIn("batchItemFailures", result)

    def test_multiple_records_all_success(self):
        mock_event = MagicMock()
        mock_event.records = [{"messageId": "msg-1"}, {"messageId": "msg-2"}, {"messageId": "msg-3"}]
        self.mock_aws_lambda_event.return_value = mock_event
        self.mock_process_record.side_effect = [
            {"status": "success"},
            {"status": "success"},
            {"status": "success"},
        ]

        result = handler(self.multi_sqs_event, None)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Successfully processed 3 records")
        self.assertNotIn("batchItemFailures", result)

    def test_single_record_error_returns_batch_item_failure(self):
        """A record returning status=error must appear in batchItemFailures — not raise."""
        mock_event = MagicMock()
        mock_event.records = [{"messageId": "msg-1"}]
        self.mock_aws_lambda_event.return_value = mock_event
        self.mock_process_record.return_value = {"status": "error", "message": "PDS timeout"}

        result = handler(self.single_sqs_event, None)

        self.assertIn("batchItemFailures", result)
        self.assertEqual(result["batchItemFailures"], [{"itemIdentifier": "msg-1"}])

    def test_mixed_batch_only_failures_in_response(self):
        """Only the failing messageId appears in batchItemFailures; successes are not listed."""
        mock_event = MagicMock()
        mock_event.records = [
            {"messageId": "msg-1"},
            {"messageId": "msg-2"},
            {"messageId": "msg-3"},
        ]
        self.mock_aws_lambda_event.return_value = mock_event
        self.mock_process_record.side_effect = [
            {"status": "success"},
            {"status": "error", "message": "PDS returned 404"},
            {"status": "success"},
        ]

        result = handler(self.multi_sqs_event, None)

        self.assertIn("batchItemFailures", result)
        self.assertEqual(result["batchItemFailures"], [{"itemIdentifier": "msg-2"}])

    def test_all_records_fail_all_in_batch_item_failures(self):
        mock_event = MagicMock()
        mock_event.records = [{"messageId": "msg-1"}, {"messageId": "msg-2"}]
        self.mock_aws_lambda_event.return_value = mock_event
        self.mock_process_record.side_effect = [
            {"status": "error", "message": "err"},
            {"status": "error", "message": "err"},
        ]

        result = handler(self.multi_sqs_event, None)

        self.assertEqual(
            result["batchItemFailures"],
            [{"itemIdentifier": "msg-1"}, {"itemIdentifier": "msg-2"}],
        )

    def test_process_record_raises_exception_is_isolated_per_record(self):
        """
        Core regression test for the alarm incident.
        If process_record throws for one record, only that messageId is in batchItemFailures.
        The other records still process normally — no full-batch failure.
        """
        mock_event = MagicMock()
        mock_event.records = [
            {"messageId": "msg-1"},
            {"messageId": "msg-2"},
            {"messageId": "msg-3"},
        ]
        self.mock_aws_lambda_event.return_value = mock_event
        self.mock_process_record.side_effect = [
            {"status": "success"},
            RuntimeError("Unexpected crash in process_record"),
            {"status": "success"},
        ]

        result = handler(self.multi_sqs_event, None)

        self.assertIn("batchItemFailures", result)
        self.assertEqual(result["batchItemFailures"], [{"itemIdentifier": "msg-2"}])
        # Verify the other two records were still processed
        self.assertEqual(self.mock_process_record.call_count, 3)

    def test_process_record_raises_logs_exception(self):
        """Unexpected exception must be logged at ERROR level."""
        mock_event = MagicMock()
        mock_event.records = [{"messageId": "msg-1"}]
        self.mock_aws_lambda_event.return_value = mock_event
        self.mock_process_record.side_effect = RuntimeError("boom")

        handler(self.single_sqs_event, None)

        self.mock_logger.exception.assert_called_once_with("Unexpected error processing messageId: %s", "msg-1")

    def test_empty_records_returns_success(self):
        mock_event = MagicMock()
        mock_event.records = []
        self.mock_aws_lambda_event.return_value = mock_event

        result = handler(self.empty_event, None)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "No records found in event")
        self.mock_process_record.assert_not_called()

    def test_no_records_key_returns_success(self):
        mock_event = MagicMock()
        mock_event.records = []
        self.mock_aws_lambda_event.return_value = mock_event

        result = handler(self.no_records_event, None)

        self.mock_process_record.assert_not_called()
        self.assertEqual(result["status"], "success")

    def test_aws_lambda_event_raises_propagates_as_exception(self):
        """
        A crash before the record loop (e.g. malformed event schema) must re-raise
        so SQS retries the full batch — nothing was processed yet.
        """
        self.mock_aws_lambda_event.side_effect = Exception("malformed event")

        with self.assertRaises(Exception, msg="malformed event"):
            handler(self.single_sqs_event, None)
