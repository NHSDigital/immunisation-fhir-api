import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from lambda_handler import extract_trace_ids, lambda_handler


class TestExtractTraceIds(unittest.TestCase):
    """Tests for extract_trace_ids helper function."""

    @classmethod
    def setUpClass(cls):
        """Load the sample SQS event once for all tests."""
        sample_event_path = Path(__file__).parent.parent / "tests/sqs_event.json"
        with open(sample_event_path, "r") as f:
            raw_event = json.load(f)

        # Convert body to JSON string if it's a dict
        if isinstance(raw_event.get("body"), dict):
            raw_event["body"] = json.dumps(raw_event["body"])

        cls.sample_sqs_event = raw_event

    def test_extract_trace_ids_success_from_real_payload(self):
        """Test successful extraction using real SQS event structure."""
        message_id, immunisation_id = extract_trace_ids(self.sample_sqs_event)

        self.assertEqual(message_id, "98ed30eb-829f-41df-8a73-57fef70cf161")
        self.assertEqual(immunisation_id, "d058014c-b0fd-4471-8db9-3316175eb825")

    def test_extract_trace_ids_missing_message_id(self):
        """Test extraction when messageId is missing."""
        record = {"body": json.dumps({"dynamodb": {"NewImage": {"ImmsID": {"S": "imms-456"}}}})}

        message_id, immunisation_id = extract_trace_ids(record)

        self.assertEqual(message_id, "unknown")
        self.assertEqual(immunisation_id, "imms-456")

    def test_extract_trace_ids_missing_body(self):
        """Test extraction when body is missing."""
        record = {"messageId": "msg-123"}

        message_id, immunisation_id = extract_trace_ids(record)

        self.assertEqual(message_id, "msg-123")
        self.assertIsNone(immunisation_id)

    def test_extract_trace_ids_invalid_json_body(self):
        """Test extraction when body contains invalid JSON."""
        record = {"messageId": "msg-123", "body": "not valid json"}

        message_id, immunisation_id = extract_trace_ids(record)

        self.assertEqual(message_id, "msg-123")
        self.assertIsNone(immunisation_id)

    def test_extract_trace_ids_missing_dynamodb_structure(self):
        """Test extraction when DynamoDB structure is incomplete."""
        record = {"messageId": "msg-123", "body": json.dumps({"other": "data"})}

        message_id, immunisation_id = extract_trace_ids(record)

        self.assertEqual(message_id, "msg-123")
        self.assertIsNone(immunisation_id)


class TestLambdaHandler(unittest.TestCase):
    """Tests for lambda_handler function."""

    @classmethod
    def setUpClass(cls):
        """Load the sample SQS event once for all tests."""
        sample_event_path = Path(__file__).parent.parent / "tests/sqs_event.json"
        with open(sample_event_path, "r") as f:
            raw_event = json.load(f)

        # Convert body to JSON string if it's a dict
        if isinstance(raw_event.get("body"), dict):
            raw_event["body"] = json.dumps(raw_event["body"])

        cls.sample_sqs_record = raw_event

    def setUp(self):
        """Set up test fixtures."""
        self.sample_notification = {
            "id": "notif-789",
            "specversion": "1.0",
            "type": "imms-vaccinations-2",
        }

        self.successful_mns_response = {"status_code": 200, "message": "Published"}

    @patch("lambda_handler.get_mns_service")
    @patch("lambda_handler.create_mns_notification")
    @patch("lambda_handler.logger")
    def test_lambda_handler_single_record_success_real_payload(
        self, mock_logger, mock_create_notification, mock_get_mns
    ):
        """Test successful processing using real SQS event payload."""
        # Mock MNS service instance
        mock_mns_service = Mock()
        mock_mns_service.publish_notification.return_value = self.successful_mns_response
        mock_get_mns.return_value = mock_mns_service

        mock_create_notification.return_value = self.sample_notification

        event = {"Records": [self.sample_sqs_record]}
        result = lambda_handler(event, Mock())

        self.assertEqual(result, {"batchItemFailures": []})
        mock_create_notification.assert_called_once_with(self.sample_sqs_record)
        mock_mns_service.publish_notification.assert_called_once_with(self.sample_notification)
        mock_logger.exception.assert_not_called()

    @patch("lambda_handler.get_mns_service")
    @patch("lambda_handler.create_mns_notification")
    @patch("lambda_handler.logger")
    def test_lambda_handler_multiple_records_all_success(self, mock_logger, mock_create_notification, mock_get_mns):
        """Test successful processing of multiple SQS records."""
        mock_mns_service = Mock()
        mock_mns_service.publish_notification.return_value = self.successful_mns_response
        mock_get_mns.return_value = mock_mns_service

        mock_create_notification.return_value = self.sample_notification

        record_2 = self.sample_sqs_record.copy()
        record_2["messageId"] = "different-message-id"

        event = {"Records": [self.sample_sqs_record, record_2]}
        result = lambda_handler(event, Mock())

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(mock_create_notification.call_count, 2)
        self.assertEqual(mock_mns_service.publish_notification.call_count, 2)
        mock_logger.exception.assert_not_called()

    @patch("lambda_handler.get_mns_service")
    @patch("lambda_handler.create_mns_notification")
    @patch("lambda_handler.logger")
    def test_lambda_handler_single_record_failure(self, mock_logger, mock_create_notification, mock_get_mns):
        """Test handling of a single record failure."""
        mock_mns_service = Mock()
        mock_get_mns.return_value = mock_mns_service

        mock_create_notification.side_effect = Exception("Processing error")

        event = {"Records": [self.sample_sqs_record]}
        result = lambda_handler(event, Mock())

        expected_message_id = self.sample_sqs_record["messageId"]
        self.assertEqual(result, {"batchItemFailures": [{"itemIdentifier": expected_message_id}]})
        mock_logger.exception.assert_called_once()
        mock_logger.warning.assert_called_once_with("Batch completed with 1 failures")
        mock_mns_service.publish_notification.assert_not_called()

    @patch("lambda_handler.get_mns_service")
    @patch("lambda_handler.create_mns_notification")
    @patch("lambda_handler.logger")
    def test_lambda_handler_mns_publish_failure(self, mock_logger, mock_create_notification, mock_get_mns):
        """Test handling when MNS publish returns non-201 status."""
        mock_mns_service = Mock()
        mock_mns_service.publish_notification.return_value = {"status_code": 400, "message": "Bad Request"}
        mock_get_mns.return_value = mock_mns_service

        mock_create_notification.return_value = self.sample_notification

        event = {"Records": [self.sample_sqs_record]}
        result = lambda_handler(event, Mock())

        expected_message_id = self.sample_sqs_record["messageId"]
        self.assertEqual(result, {"batchItemFailures": [{"itemIdentifier": expected_message_id}]})
        mock_logger.exception.assert_called_once()

    @patch("lambda_handler.get_mns_service")
    @patch("lambda_handler.create_mns_notification")
    @patch("lambda_handler.logger")
    def test_lambda_handler_partial_batch_failure(self, mock_logger, mock_create_notification, mock_get_mns):
        """Test partial batch failure where one record succeeds and one fails."""
        mock_mns_service = Mock()
        mock_mns_service.publish_notification.side_effect = [self.successful_mns_response, Exception("MNS API error")]
        mock_get_mns.return_value = mock_mns_service

        mock_create_notification.return_value = self.sample_notification

        record_2 = self.sample_sqs_record.copy()
        record_2["messageId"] = "msg-456"

        event = {"Records": [self.sample_sqs_record, record_2]}
        result = lambda_handler(event, Mock())

        self.assertEqual(len(result["batchItemFailures"]), 1)
        self.assertEqual(result["batchItemFailures"][0]["itemIdentifier"], "msg-456")
        self.assertEqual(mock_create_notification.call_count, 2)
        mock_logger.exception.assert_called_once()

    @patch("lambda_handler.get_mns_service")
    @patch("lambda_handler.create_mns_notification")
    @patch("lambda_handler.logger")
    def test_lambda_handler_empty_records(self, mock_logger, mock_create_notification, mock_get_mns):
        """Test handling of empty Records list."""
        mock_mns_service = Mock()
        mock_get_mns.return_value = mock_mns_service

        event = {"Records": []}
        result = lambda_handler(event, Mock())

        self.assertEqual(result, {"batchItemFailures": []})
        mock_create_notification.assert_not_called()
        mock_mns_service.publish_notification.assert_not_called()
        mock_logger.info.assert_called_with("Successfully processed all 0 messages")

    @patch("lambda_handler.get_mns_service")
    @patch("lambda_handler.create_mns_notification")
    @patch("lambda_handler.logger")
    def test_lambda_handler_logs_correct_trace_ids_on_failure(self, mock_logger, mock_create_notification, mock_get_mns):
        """Test that all trace IDs are logged when an error occurs."""
        mock_mns_service = Mock()
        mock_get_mns.return_value = mock_mns_service

        mock_create_notification.side_effect = Exception("Test error")

        event = {"Records": [self.sample_sqs_record]}
        lambda_handler(event, Mock())

        exception_call = mock_logger.exception.call_args
        self.assertEqual(exception_call[0][0], "Failed to process message")
        trace_ids = exception_call[1]["trace_ids"]

        self.assertEqual(trace_ids["message_id"], "98ed30eb-829f-41df-8a73-57fef70cf161")
        self.assertEqual(trace_ids["immunisation_id"], "d058014c-b0fd-4471-8db9-3316175eb825")
        self.assertEqual(trace_ids["error"], "Test error")


if __name__ == "__main__":
    unittest.main()
