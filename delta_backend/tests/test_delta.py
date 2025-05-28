import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
import os
import json
import decimal
from common.mappings import EventName, Operation, ActionFlag
from utils_for_converter_tests import ValuesForTests, RecordConfig

# Set environment variables before importing the module
## @TODO: # Note: Environment variables shared across tests, thus aligned
os.environ["AWS_SQS_QUEUE_URL"] = "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
os.environ["DELTA_TABLE_NAME"] = "my_delta_table"
os.environ["SOURCE"] = "my_source"

from delta import send_message, handler, process_record  # Import after setting environment variables

success_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
exception_response = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
fail_response = {"ResponseMetadata": {"HTTPStatusCode": 500}}

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

        self.firehose_logger_patcher = patch("delta.firehose_logger")
        self.mock_firehose_logger = self.firehose_logger_patcher.start()

        self.sqs_client_patcher = patch("delta.sqs_client")
        self.mock_sqs_client = self.sqs_client_patcher.start()

        self.delta_table_patcher=patch("delta.delta_table")
        self.mock_delta_table = self.delta_table_patcher.start()

    def tearDown(self):
        self.logger_exception_patcher.stop()
        self.logger_warning_patcher.stop()
        self.logger_error_patcher.stop()
        self.logger_info_patcher.stop()
        self.mock_firehose_logger.stop()
        self.sqs_client_patcher.stop()
        self.delta_table_patcher.stop()

    def test_send_message_success(self):
        # Arrange
        self.mock_sqs_client.send_message.return_value = {"MessageId": "123"}
        record = {"key": "value"}
        sqs_queue_url = "test-queue-url"

        # Act
        send_message(record, sqs_queue_url)

        # Assert
        self.mock_sqs_client.send_message.assert_called_once_with(
            QueueUrl=sqs_queue_url, MessageBody=json.dumps(record)
        )

    def test_send_message_client_error(self):
        # Arrange
        record = {"key": "value"}

        # Simulate ClientError
        error_response = {"Error": {"Code": "500", "Message": "Internal Server Error"}}
        self.mock_sqs_client.send_message.side_effect = ClientError(error_response, "SendMessage")

        # Act
        send_message(record, "test-queue-url")

        # Assert
        self.mock_logger_error.assert_called_once_with(
            f"Error sending record to DLQ: An error occurred (500) when calling the SendMessage operation: Internal Server Error"
        )

    def test_handler_success_insert(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = success_response
        suppliers = ["DPS", "EMIS"]
        for supplier in suppliers:
            imms_id = f"test-insert-imms-{supplier}-id"
            event = ValuesForTests.get_event(event_name=EventName.CREATE, operation=Operation.CREATE, imms_id=imms_id, supplier=supplier)

            # Act 
            result = handler(event, None)

            # Assert
            self.assertTrue(result)
            self.mock_delta_table.put_item.assert_called()
            self.mock_firehose_logger.send_log.assert_called() # check logged
            put_item_call_args = self.mock_delta_table.put_item.call_args # check data written to DynamoDB
            put_item_data = put_item_call_args.kwargs["Item"]
            self.assertIn("Imms", put_item_data)
            self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.CREATE)
            self.assertEqual(put_item_data["Operation"], Operation.CREATE)
            self.assertEqual(put_item_data["SupplierSystem"], supplier)

    def test_handler_failure(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = fail_response
        event = ValuesForTests.get_event()

        # Act
        result = handler(event, None)

        # Assert
        self.assertFalse(result)

    def test_handler_success_update(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = success_response
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(event_name=EventName.UPDATE, operation=Operation.UPDATE, imms_id=imms_id)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_called()
        self.mock_firehose_logger.send_log.assert_called() # check logged
        put_item_call_args = self.mock_delta_table.put_item.call_args # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.UPDATE)
        self.assertEqual(put_item_data["Operation"], Operation.UPDATE)
        self.assertEqual(put_item_data["ImmsID"], imms_id)

    def test_handler_success_delete_physical(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = success_response
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(event_name=EventName.DELETE_PHYSICAL, operation=Operation.DELETE_PHYSICAL, imms_id=imms_id)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_called()
        self.mock_firehose_logger.send_log.assert_called() # check logged
        put_item_call_args = self.mock_delta_table.put_item.call_args # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Operation"], Operation.DELETE_PHYSICAL)
        self.assertEqual(put_item_data["ImmsID"], imms_id)
        self.assertEqual(put_item_data["Imms"], "")     # check imms has been blanked out

    def test_handler_success_delete_logical(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = success_response
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(event_name=EventName.UPDATE,
                                         operation=Operation.DELETE_LOGICAL, 
                                         imms_id=imms_id)
        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_called()
        self.mock_firehose_logger.send_log.assert_called() # check logged
        put_item_call_args = self.mock_delta_table.put_item.call_args # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.DELETE_LOGICAL)
        self.assertEqual(put_item_data["Operation"], Operation.DELETE_LOGICAL)
        self.assertEqual(put_item_data["ImmsID"], imms_id)

    @patch("delta.logger.info") 
    def test_dps_record_skipped(self, mock_logger_info):
        event = ValuesForTests.get_event(supplier="DPSFULL")

        response = handler(event, None)

        self.assertTrue(response)

        # Check logging and Firehose were called
        mock_logger_info.assert_called_with("Record from DPS skipped for 12345")

    @patch("delta.Converter")
    def test_partial_success_with_errors(self, mock_converter):
        mock_converter_instance = MagicMock()
        mock_converter_instance.run_conversion.return_value = {"ABC":"DEF"}
        mock_converter_instance.get_error_records.return_value = [{"error": "Invalid field"}]
        mock_converter.return_value = mock_converter_instance

        # Mock DynamoDB put_item success
        self.mock_delta_table.put_item.return_value = success_response

        event = ValuesForTests.get_event()

        response = handler(event, None)

        self.assertTrue(response)
        # Check logging and Firehose were called
        self.mock_logger_info.assert_called()
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 1)
        self.mock_firehose_logger.send_log.assert_called_once()

        # Get the actual argument passed to send_log
        args, kwargs = self.mock_firehose_logger.send_log.call_args
        sent_payload = args[0]  # First positional arg

        # Navigate to the specific message
        status_desc = sent_payload["event"]["operation_outcome"]["statusDesc"]

        # Assert the expected message is present
        self.assertIn(
            "Partial success: successfully synced into delta, but issues found within record",
            status_desc
        )

    def test_send_message_multi_records_diverse(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = success_response
        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "id2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_LOGICAL, Operation.DELETE_LOGICAL, "id3", ActionFlag.DELETE_LOGICAL),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "id4"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, len(records_config))
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, len(records_config))

    def test_send_message_skipped_records_diverse(self):
        '''Check skipped records sent to firehose but not to DynamoDB'''
        # Arrange
        self.mock_delta_table.put_item.return_value = success_response
        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "id2", ActionFlag.UPDATE),
            RecordConfig(EventName.CREATE, Operation.CREATE, "id-skip", ActionFlag.CREATE, "DPSFULL"),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "id4"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, len(records_config))

    def test_send_message_multi_create(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = success_response
        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id1", ActionFlag.CREATE),
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id2", ActionFlag.CREATE),
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id3", ActionFlag.CREATE)
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 3)


    def test_send_message_multi_update(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = success_response
        records_config = [
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id1", ActionFlag.UPDATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id2", ActionFlag.UPDATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id3", ActionFlag.UPDATE)
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 3)

    def test_send_message_multi_logical_delete(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = success_response

        records_config = [
            RecordConfig(EventName.DELETE_LOGICAL, Operation.DELETE_LOGICAL, "delete-id1", ActionFlag.DELETE_LOGICAL),
            RecordConfig(EventName.DELETE_LOGICAL, Operation.DELETE_LOGICAL, "delete-id2", ActionFlag.DELETE_LOGICAL),
            RecordConfig(EventName.DELETE_LOGICAL, Operation.DELETE_LOGICAL, "delete-id3", ActionFlag.DELETE_LOGICAL)
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 3)

    def test_send_message_multi_physical_delete(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = success_response
        records_config = [
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id1"),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id2"),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id3")
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 3)

    def test_single_error_in_multi(self):
        # Arrange
        self.mock_delta_table.put_item.side_effect = [ success_response, fail_response, success_response]

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "fail-id1.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id1.3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertFalse(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 3)
        self.assertEqual(self.mock_logger_warning.call_count, 1)

    def test_single_exception_in_multi(self):
        # Arrange
        # 2nd record fails
        self.mock_delta_table.put_item.side_effect = [success_response, exception_response, success_response]

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id2.1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "exception-id2.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id2.3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertFalse(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, len(records_config))
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, len(records_config))

    @patch("delta.process_record")
    @patch("delta.send_firehose")
    def test_handler_calls_process_record_for_each_event(self, mock_send_firehose, mock_process_record):
        # Arrange
        event = {
            "Records": [
                { "a": "record1" },
                { "a": "record2" },
                { "a": "record3" }
            ]
        }
        # Mock process_record to always return True
        mock_process_record.return_value = True, {}
        mock_send_firehose.return_value = None

        # Act
        result = handler(event, {})

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_process_record.call_count, len(event["Records"]))

    # TODO depedency injection needed here
    @patch("delta.process_record")
    @patch("delta.send_firehose")
    def test_handler_sends_all_to_firehose(self, mock_send_firehose, mock_process_record):
        # Arrange

        # event with 3 records
        event = {
            "Records": [
                { "a": "record1" },
                { "a": "record2" },
                { "a": "record3" }
            ]
        }
        return_ok = (True, {})
        return_fail = (False, {})
        mock_send_firehose.return_value = None
        mock_process_record.side_effect = [return_ok, return_fail, return_ok]

        # Act
        result = handler(event, {})

        # Assert
        self.assertFalse(result)
        self.assertEqual(mock_process_record.call_count, len(event["Records"]))
        # check that all records were sent to firehose
        self.assertEqual(mock_send_firehose.call_count, len(event["Records"]))

class DeltaRecordProcessorTestCase(unittest.TestCase):

    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.logger_warning_patcher = patch("logging.Logger.warning")
        self.mock_logger_warning = self.logger_warning_patcher.start()

        self.delta_table_patcher=patch("delta.delta_table")
        self.mock_delta_table = self.delta_table_patcher.start()

    def tearDown(self):
        self.logger_exception_patcher.stop()
        self.logger_warning_patcher.stop()
        self.logger_info_patcher.stop()
        self.delta_table_patcher.stop()

    def test_multi_record_success(self):

        # Arrange
        self.mock_delta_table.put_item.return_value = success_response
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
            result, log_data = process_record(record, {})

            # Assert
            self.assertEqual(result, True)
            operation_outcome = log_data["operation_outcome"]
            self.assertEqual(operation_outcome["record"], config.imms_id)
            self.assertEqual(operation_outcome["operation_type"], config.operation)
            self.assertEqual(operation_outcome["statusCode"], "200")
            self.assertEqual(operation_outcome["statusDesc"], "Successfully synched into delta")
            self.assertEqual(self.mock_delta_table.put_item.call_count, test_index)

        self.assertEqual(self.mock_logger_exception.call_count, 0)
        self.assertEqual(self.mock_logger_warning.call_count, 0)

    def test_multi_record_success_with_fail(self):

        # Arrange
        expected_returns = [ True, False, True]
        self.mock_delta_table.put_item.side_effect = [success_response, fail_response, success_response]
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
            log_data = {}
            # Act
            result, log_data = process_record(record, log_data)

            # Assert
            self.assertEqual(result, expected_returns[test_index-1])
            self.assertEqual(self.mock_delta_table.put_item.call_count, test_index)

        self.assertEqual(self.mock_logger_exception.call_count, 0)
        self.assertEqual(self.mock_logger_warning.call_count, 1)


    def test_single_record_table_exception(self):

        # Arrange
        imms_id = "exception-id"
        record = ValuesForTests.get_event_record(
            imms_id,
            event_name=EventName.UPDATE,
            operation=Operation.UPDATE,
            supplier="EMIS",
        )
        self.mock_delta_table.put_item.return_value = exception_response
        # Act
        result, log_data = process_record(record, {})

        # Assert
        self.assertEqual(result, False)
        operation_outcome = log_data["operation_outcome"]
        self.assertEqual(operation_outcome["record"], imms_id)
        self.assertEqual(operation_outcome["operation_type"], Operation.UPDATE)
        self.assertEqual(operation_outcome["statusCode"], "500")
        self.assertEqual(operation_outcome["statusDesc"], "Exception")
        self.assertEqual(self.mock_delta_table.put_item.call_count, 1)
        self.assertEqual(self.mock_logger_exception.call_count, 1)

    @patch("delta.json.loads")
    def test_json_loads_called_with_parse_float_decimal(self, mock_json_loads):

        # Arrange
        record = ValuesForTests.get_event_record(
            imms_id="id",
            event_name=EventName.UPDATE,
            operation=Operation.UPDATE
        )
        record["dynamodb"]["NewImage"]["Resource"]["S"] = f'{{"float_value": "1.23"}}'

        self.mock_delta_table.put_item.return_value = success_response
        # Act
        process_record(record, {})

        # Assert
        mock_json_loads.assert_any_call('{"float_value": "1.23"}', parse_float=decimal.Decimal)
        


import delta

class TestGetDeltaTable(unittest.TestCase):
    def setUp(self):
        self.delta_table_patcher=patch("delta.delta_table")
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

    @patch("boto3.resource")
    def test_returns_cached_table(self, mock_boto3_resource):
        delta.delta_table = self.mock_delta_table

        table = delta.get_delta_table()
        self.assertIs(table, self.mock_delta_table)
        # Should not call boto3 again
        mock_boto3_resource.assert_not_called()

    # mock boto3.resource to raise an exception
    @patch("boto3.resource")
    def test_returns_none_on_exception(self, mock_boto3_resource):
        delta.delta_table = None
        mock_boto3_resource.side_effect = Exception("fail")
        table = delta.get_delta_table()
        self.assertIsNone(table)
        self.mock_logger_error.assert_called()

import delta

class TestGetSqsClient(unittest.TestCase):
    def setUp(self):
        # Patch logger.info and logger.error
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()
        self.sqs_client_patcher = patch("delta.boto3.client")
        self.mock_sqs_client = self.sqs_client_patcher.start()
        # Reset the global sqs_client before each test
        delta.sqs_client = None

    def tearDown(self):
        self.logger_info_patcher.stop()
        self.logger_error_patcher.stop()
        self.sqs_client_patcher.stop()

    def test_returns_client_on_success(self):
        mock_client = MagicMock()
        self.mock_sqs_client.return_value = mock_client

        client = delta.get_sqs_client()
        self.assertIs(client, mock_client)
        # Should cache the client
        self.assertIs(delta.sqs_client, mock_client)

    def test_returns_cached_client(self):
        mock_client = MagicMock()
        delta.sqs_client = mock_client

        client = delta.get_sqs_client()
        self.assertIs(client, mock_client)
        # Should not re-initialize
        self.mock_sqs_client.assert_not_called()

    def test_returns_none_on_exception(self):
        self.mock_sqs_client.side_effect = Exception("fail")
        client = delta.get_sqs_client()
        self.assertIsNone(client)
        self.mock_logger_error.assert_called()


import delta

class TestSendMessage(unittest.TestCase):
    def setUp(self):
        self.get_sqs_client_patcher = patch("delta.get_sqs_client")
        self.mock_get_sqs_client = self.get_sqs_client_patcher.start()
        self.mock_sqs_client = MagicMock()
        self.mock_get_sqs_client.return_value = self.mock_sqs_client

        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()

    def tearDown(self):
        self.get_sqs_client_patcher.stop()
        self.logger_info_patcher.stop()
        self.logger_error_patcher.stop()

    def test_send_message_success(self):
        record = {"a": "bbb"}
        self.mock_sqs_client.send_message.return_value = {"MessageId": "123"}

        delta.send_message(record)

        self.mock_sqs_client.send_message.assert_called_once()
        self.mock_logger_info.assert_any_call("Record saved successfully to the DLQ")
        self.mock_logger_error.assert_not_called()

    def test_send_message_client_error(self):
        record = {"a": "bbb"}
        self.mock_sqs_client.send_message.side_effect = Exception("SQS error")

        delta.send_message(record, "test-queue-url")

        self.mock_logger_error.assert_called()
