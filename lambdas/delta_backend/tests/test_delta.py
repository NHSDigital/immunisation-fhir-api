import decimal
import json
import os
import unittest
from unittest.mock import MagicMock, call, patch

from botocore.exceptions import ClientError

import delta
from delta import (
    handler,
    process_record,
    send_record_to_dlq,
)
from mappings import ActionFlag, EventName, Operation
from utils_for_converter_tests import RecordConfig, ValuesForTests

TEST_DEAD_LETTER_QUEUE_URL = "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
os.environ["AWS_SQS_QUEUE_URL"] = TEST_DEAD_LETTER_QUEUE_URL
os.environ["DELTA_TABLE_NAME"] = "my_delta_table"
os.environ["DELTA_TTL_DAYS"] = "14"
os.environ["SOURCE"] = "my_source"

SUCCESS_RESPONSE = {"ResponseMetadata": {"HTTPStatusCode": 200}}
DUPLICATE_RESPONSE = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
EXCEPTION_RESPONSE = ClientError({"Error": {"Code": "InternalServerError"}}, "PutItem")
FAIL_RESPONSE = {"ResponseMetadata": {"HTTPStatusCode": 500}}


class DeltaHandlerTestCase(unittest.TestCase):
    # TODO refactor for dependency injection, eg process_record, send_firehose etc
    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.logger_warning_patcher = patch("logging.Logger.warning")
        self.mock_logger_warning = self.logger_warning_patcher.start()

        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()

        self.send_log_to_firehose_patcher = patch("delta.send_log_to_firehose")
        self.mock_send_log_to_firehose = self.send_log_to_firehose_patcher.start()

        self.sqs_client_patcher = patch("common.clients.global_sqs_client")
        self.mock_sqs_client = self.sqs_client_patcher.start()

        self.delta_table_patcher = patch("delta.delta_table")
        self.mock_delta_table = self.delta_table_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_send_record_to_dlq_success(self):
        # Arrange
        self.mock_sqs_client.send_message.return_value = {"MessageId": "123"}
        record = {"key": "value"}

        # Act
        send_record_to_dlq(record)

        # Assert
        self.mock_sqs_client.send_message.assert_called_once_with(
            QueueUrl=TEST_DEAD_LETTER_QUEUE_URL, MessageBody=json.dumps(record)
        )
        self.mock_logger_info.assert_called_with("Record saved successfully to the DLQ")

    def test_send_record_to_dlq_client_error(self):
        # Arrange
        record = {"key": "value"}

        # Simulate ClientError
        error_response = {"Error": {"Code": "500", "Message": "Internal Server Error"}}
        self.mock_sqs_client.send_message.side_effect = ClientError(error_response, "SendMessage")

        # Act
        send_record_to_dlq(record)

        # Assert
        self.mock_logger_exception.assert_called_once_with("Error sending record to DLQ")

    def test_handler_success_insert(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        suppliers = ["RAVS", "EMIS"]
        for supplier in suppliers:
            imms_id = f"test-insert-imms-{supplier}-id"
            event = ValuesForTests.get_event(
                event_name=EventName.CREATE,
                operation=Operation.CREATE,
                imms_id=imms_id,
                supplier=supplier,
            )

            # Act
            result = handler(event, None)

            # Assert
            self.assertTrue(result)
            self.mock_delta_table.put_item.assert_called()
            self.mock_send_log_to_firehose.assert_called()  # check logged
            put_item_call_args = self.mock_delta_table.put_item.call_args  # check data written to DynamoDB
            put_item_data = put_item_call_args.kwargs["Item"]
            self.assertIn("Imms", put_item_data)
            self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.CREATE)
            self.assertEqual(put_item_data["Operation"], Operation.CREATE)
            self.assertEqual(put_item_data["SupplierSystem"], supplier)
            self.mock_sqs_client.send_message.assert_not_called()

    def test_handler_exception(self):
        """Ensure that sqs_client exceptions do not cause the lambda handler itself to raise an exception"""
        # Arrange
        self.mock_sqs_client.send_message.side_effect = Exception("SQS error")
        self.mock_delta_table.put_item.return_value = FAIL_RESPONSE
        event = ValuesForTests.get_event()

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_logger_exception.assert_has_calls(
            [
                call("Error sending record to DLQ"),
            ]
        )

    def test_handler_raises_exception_if_called_with_unexpected_event(self):
        """Tests that when the Lambda is invoked with an unexpected event format i.e. no "Records" key, then an
        exception will be raised. The DDB Stream configuration will then ensure that the event is forwarded to the DLQ.
        Note: this would only ever happen if we misconfigured the Lambda or tested manually with a bad event."""
        # Arrange
        event = {"invalid_format": True}

        # Act
        with self.assertRaises(KeyError):
            handler(event, None)

        # Assert
        self.mock_sqs_client.send_message.assert_not_called()

    def test_handler_processing_failure(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = FAIL_RESPONSE
        event = ValuesForTests.get_event()

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_sqs_client.send_message.assert_called_with(
            QueueUrl=TEST_DEAD_LETTER_QUEUE_URL, MessageBody=json.dumps(event["Records"][0])
        )

    def test_handler_success_update(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(event_name=EventName.UPDATE, operation=Operation.UPDATE, imms_id=imms_id)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_called()
        self.mock_send_log_to_firehose.assert_called()  # check logged
        put_item_call_args = self.mock_delta_table.put_item.call_args  # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.UPDATE)
        self.assertEqual(put_item_data["Operation"], Operation.UPDATE)
        self.assertEqual(put_item_data["ImmsID"], imms_id)
        self.mock_sqs_client.send_message.assert_not_called()

    def test_handler_success_delete_physical(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(
            event_name=EventName.DELETE_PHYSICAL,
            operation=Operation.DELETE_PHYSICAL,
            imms_id=imms_id,
        )

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_called()
        self.mock_send_log_to_firehose.assert_called()  # check logged
        put_item_call_args = self.mock_delta_table.put_item.call_args  # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Operation"], Operation.DELETE_PHYSICAL)
        self.assertEqual(put_item_data["ImmsID"], imms_id)
        self.assertEqual(put_item_data["Imms"], "")  # check imms has been blanked out
        self.mock_sqs_client.send_message.assert_not_called()

    def test_handler_success_delete_logical(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(
            event_name=EventName.UPDATE,
            operation=Operation.DELETE_LOGICAL,
            imms_id=imms_id,
        )
        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_called()
        self.mock_send_log_to_firehose.assert_called()  # check logged
        put_item_call_args = self.mock_delta_table.put_item.call_args  # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.DELETE_LOGICAL)
        self.assertEqual(put_item_data["Operation"], Operation.DELETE_LOGICAL)
        self.assertEqual(put_item_data["ImmsID"], imms_id)
        self.mock_sqs_client.send_message.assert_not_called()

    @patch("delta.logger.info")
    def test_dps_record_skipped(self, mock_logger_info):
        event = ValuesForTests.get_event(supplier="DPSFULL")

        response = handler(event, None)

        self.assertTrue(response)

        # Check logging and Firehose were called
        mock_logger_info.assert_called_with("Record from DPS skipped")
        self.mock_send_log_to_firehose.assert_called()
        self.mock_sqs_client.send_message.assert_not_called()

    @patch("delta.Converter")
    def test_partial_success_with_errors(self, mock_converter):
        mock_converter_instance = MagicMock()
        mock_converter_instance.run_conversion.return_value = {"ABC": "DEF"}
        mock_converter_instance.get_error_records.return_value = [{"error": "Invalid field"}]
        mock_converter.return_value = mock_converter_instance

        # Mock DynamoDB put_item success
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE

        event = ValuesForTests.get_event()

        response = handler(event, None)

        self.assertTrue(response)
        # Check logging and Firehose were called
        self.mock_logger_info.assert_called()
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 1)
        self.mock_send_log_to_firehose.assert_called_once()

        # Get the actual argument passed to send_log_to_firehose
        args, kwargs = self.mock_send_log_to_firehose.call_args
        sent_payload = args[1]  # Second positional arg

        # Navigate to the specific message
        status_desc = sent_payload["operation_outcome"]["statusDesc"]

        # Assert the expected message is present
        self.assertIn(
            "Partial success: successfully synced into delta, but issues found within record",
            status_desc,
        )

    def test_send_message_multi_records_diverse(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "id2", ActionFlag.UPDATE),
            RecordConfig(
                EventName.DELETE_LOGICAL,
                Operation.DELETE_LOGICAL,
                "id3",
                ActionFlag.DELETE_LOGICAL,
            ),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "id4"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, len(records_config))
        self.assertEqual(self.mock_send_log_to_firehose.call_count, len(records_config))

    def test_send_message_skipped_records_diverse(self):
        """Check skipped records sent to firehose but not to DynamoDB"""
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "id2", ActionFlag.UPDATE),
            RecordConfig(
                EventName.CREATE,
                Operation.CREATE,
                "id-skip",
                ActionFlag.CREATE,
                "DPSFULL",
            ),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "id4"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, len(records_config))

    def test_send_message_multi_create(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id1", ActionFlag.CREATE),
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id2", ActionFlag.CREATE),
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id3", ActionFlag.CREATE),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)

    def test_send_message_multi_update(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        records_config = [
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id1", ActionFlag.UPDATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id2", ActionFlag.UPDATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id3", ActionFlag.UPDATE),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)

    def test_send_message_multi_logical_delete(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE

        records_config = [
            RecordConfig(
                EventName.DELETE_LOGICAL,
                Operation.DELETE_LOGICAL,
                "delete-id1",
                ActionFlag.DELETE_LOGICAL,
            ),
            RecordConfig(
                EventName.DELETE_LOGICAL,
                Operation.DELETE_LOGICAL,
                "delete-id2",
                ActionFlag.DELETE_LOGICAL,
            ),
            RecordConfig(
                EventName.DELETE_LOGICAL,
                Operation.DELETE_LOGICAL,
                "delete-id3",
                ActionFlag.DELETE_LOGICAL,
            ),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)

    def test_send_message_multi_physical_delete(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        records_config = [
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id1"),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id2"),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)

    def test_single_error_in_multi(self):
        # Arrange
        self.mock_delta_table.put_item.side_effect = [
            SUCCESS_RESPONSE,
            FAIL_RESPONSE,
            SUCCESS_RESPONSE,
        ]

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "fail-id1.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id1.3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)
        self.assertEqual(self.mock_logger_error.call_count, 1)
        self.assertEqual(self.mock_sqs_client.send_message.call_count, 1)

    def test_single_exception_in_multi(self):
        # Arrange
        # 2nd record fails
        self.mock_delta_table.put_item.side_effect = [
            SUCCESS_RESPONSE,
            EXCEPTION_RESPONSE,
            SUCCESS_RESPONSE,
        ]

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id2.1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "exception-id2.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id2.3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_sqs_client.send_message.call_count, 1)
        self.assertEqual(self.mock_delta_table.put_item.call_count, len(records_config))
        self.assertEqual(self.mock_send_log_to_firehose.call_count, len(records_config))

    def test_single_duplicate_in_multi(self):
        # Arrange
        self.mock_delta_table.put_item.side_effect = [
            SUCCESS_RESPONSE,
            DUPLICATE_RESPONSE,
            SUCCESS_RESPONSE,
        ]

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id2.1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "duplicate-id2.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id2.3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, len(records_config))
        self.assertEqual(self.mock_send_log_to_firehose.call_count, len(records_config))

    @patch("delta.process_record")
    @patch("delta.send_log_to_firehose")
    def test_handler_calls_process_record_for_each_event(self, mock_send_log_to_firehose, mock_process_record):
        # Arrange
        event = {"Records": [{"a": "record1"}, {"a": "record2"}, {"a": "record3"}]}
        # Mock process_record to always return True
        mock_process_record.return_value = True, {}
        mock_send_log_to_firehose.return_value = None

        # Act
        result = handler(event, {})

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_process_record.call_count, len(event["Records"]))

    @patch("delta.process_record")
    @patch("delta.send_log_to_firehose")
    def test_handler_sends_all_to_firehose(self, mock_send_log_to_firehose, mock_process_record):
        # event with 3 records
        event = {"Records": [{"a": "record1"}, {"a": "record2"}, {"a": "record3"}]}
        return_ok = (True, {})
        return_fail = (False, {})
        mock_send_log_to_firehose.return_value = None
        mock_process_record.side_effect = [return_ok, return_fail, return_ok]

        # Act
        result = handler(event, {})

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_process_record.call_count, len(event["Records"]))
        # check that all records were sent to firehose
        self.assertEqual(mock_send_log_to_firehose.call_count, len(event["Records"]))
        # Only send the failed record to SQS DLQ
        self.assertEqual(self.mock_sqs_client.send_message.call_count, 1)


class DeltaRecordProcessorTestCase(unittest.TestCase):
    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_warning_patcher = patch("logging.Logger.warning")
        self.mock_logger_warning = self.logger_warning_patcher.start()

        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()

        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.delta_table_patcher = patch("delta.delta_table")
        self.mock_delta_table = self.delta_table_patcher.start()

    def tearDown(self):
        self.logger_exception_patcher.stop()
        self.logger_warning_patcher.stop()
        self.logger_info_patcher.stop()
        self.delta_table_patcher.stop()

    def test_multi_record_success(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        test_configs = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id.1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "ok-id.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id.3"),
        ]
        test_index = 0
        for config in test_configs:
            test_index += 1
            record = ValuesForTests.get_event_record(
                imms_id=config.imms_id,
                event_name=config.event_name,
                operation=config.operation,
                supplier=config.supplier,
            )
            # Act
            result, operation_outcome = process_record(record)

            # Assert
            self.assertEqual(result, True)
            self.assertEqual(operation_outcome["record"], config.imms_id)
            self.assertEqual(operation_outcome["operation_type"], config.operation)
            self.assertEqual(operation_outcome["statusCode"], "200")
            self.assertEqual(operation_outcome["statusDesc"], "Successfully synched into delta")
            self.assertEqual(self.mock_delta_table.put_item.call_count, test_index)

        self.assertEqual(self.mock_logger_exception.call_count, 0)
        self.assertEqual(self.mock_logger_warning.call_count, 0)

    def test_multi_record_success_with_fail(self):
        # Arrange
        expected_returns = [True, False, True]
        self.mock_delta_table.put_item.side_effect = [
            SUCCESS_RESPONSE,
            FAIL_RESPONSE,
            SUCCESS_RESPONSE,
        ]
        test_configs = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id.1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "fail-id.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id.3"),
        ]
        test_index = 0
        for config in test_configs:
            test_index += 1
            record = ValuesForTests.get_event_record(
                imms_id=config.imms_id,
                event_name=config.event_name,
                operation=config.operation,
                supplier=config.supplier,
            )
            # Act
            result, _ = process_record(record)

            # Assert
            self.assertEqual(result, expected_returns[test_index - 1])
            self.assertEqual(self.mock_delta_table.put_item.call_count, test_index)

        self.assertEqual(self.mock_logger_error.call_count, 1)

    def test_single_record_table_exception(self):
        # Arrange
        imms_id = "exception-id"
        record = ValuesForTests.get_event_record(
            imms_id,
            event_name=EventName.UPDATE,
            operation=Operation.UPDATE,
            supplier="EMIS",
        )
        self.mock_delta_table.put_item.side_effect = EXCEPTION_RESPONSE
        # Act
        result, operation_outcome = process_record(record)

        # Assert
        self.assertEqual(result, False)
        self.assertEqual(operation_outcome["record"], imms_id)
        self.assertEqual(operation_outcome["operation_type"], Operation.UPDATE)
        self.assertEqual(operation_outcome["statusCode"], "500")
        self.assertEqual(operation_outcome["statusDesc"], "Exception")
        self.assertEqual(self.mock_delta_table.put_item.call_count, 1)
        self.assertEqual(self.mock_logger_exception.call_count, 1)

    @patch("delta.json.loads")
    def test_json_loads_called_with_parse_float_decimal(self, mock_json_loads):
        # Arrange
        record = ValuesForTests.get_event_record(imms_id="id", event_name=EventName.UPDATE, operation=Operation.UPDATE)

        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        # Act
        process_record(record)

        # Assert
        mock_json_loads.assert_any_call(ValuesForTests.json_value_for_test, parse_float=decimal.Decimal)


class TestGetDeltaTable(unittest.TestCase):
    def setUp(self):
        self.delta_table_patcher = patch("delta.delta_table")
        self.mock_delta_table = self.delta_table_patcher.start()
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()

    def tearDown(self):
        self.delta_table_patcher.stop()
        self.logger_info_patcher.stop()
        self.logger_error_patcher.stop()

    def test_returns_table_on_success(self):
        table = delta.get_delta_table()
        self.assertIs(table, self.mock_delta_table)
        # Should cache the table
        self.assertIs(delta.delta_table, self.mock_delta_table)

    @patch("delta.get_dynamodb_table")
    def test_returns_cached_table(self, mock_get_dynamodb_table):
        delta.delta_table = self.mock_delta_table

        table = delta.get_delta_table()
        self.assertIs(table, self.mock_delta_table)
        # Should not call get_dynamodb_table again
        mock_get_dynamodb_table.assert_not_called()

    # mock get_dynamodb_table to raise an exception
    @patch("delta.get_dynamodb_table")
    def test_returns_none_on_exception(self, mock_get_dynamodb_table):
        delta.delta_table = None
        mock_get_dynamodb_table.side_effect = Exception("fail")
        table = delta.get_delta_table()
        self.assertIsNone(table)
        self.mock_logger_error.assert_called()
