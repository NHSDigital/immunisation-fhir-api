import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
import os
import json
from common.mappings import EventName, Operation, ActionFlag

# Set environment variables before importing the module
## @TODO: # Note: Environment variables shared across tests, thus aligned
os.environ["AWS_SQS_QUEUE_URL"] = "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
os.environ["DELTA_TABLE_NAME"] = "my_delta_table"
os.environ["SOURCE"] = "my_source"

from delta import send_message, handler  # Import after setting environment variables
from utils_for_converter_tests import ValuesForTests, RecordConfig

success_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
exception_response = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
fail_response = {"ResponseMetadata": {"HTTPStatusCode": 500}}

class DeltaTestCase(unittest.TestCase):

    def setUp(self):
        # Common setup if needed
        self.context = {}
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.logger_warning_patcher = patch("logging.Logger.warning")
        self.mock_logger_warning = self.logger_warning_patcher.start()

        self.firehose_logger_patcher = patch("delta.firehose_logger")
        self.mock_firehose_logger = self.firehose_logger_patcher.start()
        
        self.boto_client_patcher = patch("boto3.client")
        self.mock_boto_client = self.boto_client_patcher.start()


    def tearDown(self):
        self.logger_exception_patcher.stop()
        self.logger_warning_patcher.stop()
        self.logger_info_patcher.stop()
        self.mock_firehose_logger.stop()
        self.boto_client_patcher.stop()

    @staticmethod
    def setup_mock_sqs(mock_boto_client, return_value={"ResponseMetadata": {"HTTPStatusCode": 200}}):
        mock_sqs = mock_boto_client.return_value
        mock_sqs.send_message.return_value = return_value
        return mock_sqs

    @staticmethod
    def setup_mock_dynamodb(mock_boto_resource, status_code=200):
        mock_dynamodb = mock_boto_resource.return_value
        mock_table = mock_dynamodb.Table.return_value
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": status_code}}
        return mock_table

    def setUp_mock_resources(self, mock_boto_resource, mock_boto_client):
        mock_dynamodb = mock_boto_resource.return_value
        mock_table = mock_dynamodb.Table.return_value
        mock_boto_client.return_value = {"key": "value"}
        mock_table.put_item.side_effect = Exception("Test Exception")
        return mock_table

    def test_send_message_success(self):
        # Arrange
        mock_sqs = self.setup_mock_sqs(self.mock_boto_client)
        record = {"key": "value"}

        # Act
        send_message(record)

        # Assert
        mock_sqs.send_message.assert_called_once_with(
            QueueUrl=os.environ["AWS_SQS_QUEUE_URL"], MessageBody=json.dumps(record)
        )

    @patch("boto3.client")
    @patch("logging.Logger.error")
    def test_send_message_client_error(self, mock_logger_error, mock_boto_client):
        # Arrange
        mock_sqs = MagicMock()
        mock_boto_client.return_value = mock_sqs
        record = {"key": "value"}

        # Simulate ClientError
        error_response = {"Error": {"Code": "500", "Message": "Internal Server Error"}}
        mock_sqs.send_message.side_effect = ClientError(error_response, "SendMessage")

        # Act
        send_message(record)

        # Assert
        mock_logger_error.assert_called_once_with(
            f"Error sending record to DLQ: An error occurred (500) when calling the SendMessage operation: Internal Server Error"
        )

    @patch("boto3.resource")
    def test_handler_success_insert(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)
        suppilers = ["DPS", "EMIS"]
        for supplier in suppilers:
            imms_id = f"test-insert-imms-{supplier}-id"
            event = ValuesForTests.get_event(event_name=EventName.CREATE, operation=Operation.CREATE, imms_id=imms_id, supplier=supplier)

            # Act
            result = handler(event, self.context)

            # Assert
            self.assertTrue(result)
            mock_table.put_item.assert_called()
            self.mock_firehose_logger.send_log.assert_called() # check logged
            put_item_call_args = mock_table.put_item.call_args # check data written to DynamoDB
            put_item_data = put_item_call_args.kwargs["Item"]
            self.assertIn("Imms", put_item_data)
            self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.CREATE)
            self.assertEqual(put_item_data["Operation"], Operation.CREATE)
            self.assertEqual(put_item_data["SupplierSystem"], supplier)

    @patch("boto3.resource")
    def test_handler_failure(self, mock_boto_resource):
        # Arrange
        self.setup_mock_dynamodb(mock_boto_resource, status_code=500)
        event = ValuesForTests.get_event()

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertFalse(result)

    @patch("boto3.resource")
    def test_handler_success_update(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)
        self.setup_mock_dynamodb(mock_boto_resource)
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(event_name=EventName.UPDATE, operation=Operation.UPDATE, imms_id=imms_id)

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertTrue(result)
        mock_table.put_item.assert_called()
        self.mock_firehose_logger.send_log.assert_called() # check logged
        put_item_call_args = mock_table.put_item.call_args # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.UPDATE)
        self.assertEqual(put_item_data["Operation"], Operation.UPDATE)
        self.assertEqual(put_item_data["ImmsID"], imms_id)

    @patch("boto3.resource")
    def test_handler_success_delete_physical(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(event_name=EventName.DELETE_PHYSICAL, operation=Operation.DELETE_PHYSICAL, imms_id=imms_id)

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertTrue(result)
        mock_table.put_item.assert_called()
        self.mock_firehose_logger.send_log.assert_called() # check logged
        put_item_call_args = mock_table.put_item.call_args # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Operation"], Operation.DELETE_PHYSICAL)
        self.assertEqual(put_item_data["ImmsID"], imms_id)
        self.assertEqual(put_item_data["Imms"], "")     # check imms has been blanked out

    @patch("boto3.resource")
    def test_handler_success_delete_logical(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(event_name=EventName.UPDATE,
                                         operation=Operation.DELETE_LOGICAL, 
                                         imms_id=imms_id)
        # Act
        result = handler(event, self.context)

        # Assert
        self.assertTrue(result)
        mock_table.put_item.assert_called()
        self.mock_firehose_logger.send_log.assert_called() # check logged
        put_item_call_args = mock_table.put_item.call_args # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.DELETE_LOGICAL)
        self.assertEqual(put_item_data["Operation"], Operation.DELETE_LOGICAL)
        self.assertEqual(put_item_data["ImmsID"], imms_id)


    @patch("delta.logger.info") 
    def test_dps_record_skipped(self, mock_logger_info):
        event = ValuesForTests.get_event(supplier="DPSFULL")
        context = {}

        response = handler(event, context)

        self.assertTrue(response)

        # Check logging and Firehose were called
        mock_logger_info.assert_called_with("Record from DPS skipped for 12345")

    # TODO - amend test once error handling implemented
    @patch("delta.logger.info")
    @patch("Converter.Converter")
    @patch("delta.boto3.resource")
    def test_partial_success_with_errors(self, mock_dynamodb, mock_converter, mock_logger_info):
        mock_converter_instance = MagicMock()
        mock_converter_instance.runConversion.return_value = [{}]
        mock_converter_instance.getErrorRecords.return_value = [{"error": "Invalid field"}]
        mock_converter.return_value = mock_converter_instance

        # Mock DynamoDB put_item success
        mock_table = MagicMock()
        mock_dynamodb.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        event = ValuesForTests.get_event()
        context = {}

        response = handler(event, context)

        # self.assertEqual(response["statusCode"], 207)
        # self.assertIn("Partial success", response["body"])

        # Check logging and Firehose were called
        # mock_logger_info.assert_called()
        # mock_firehose_send_log.assert_called()

    @patch("boto3.resource")
    def test_send_message_multi_records_diverse(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "id2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_LOGICAL, Operation.DELETE_LOGICAL, "id3", ActionFlag.DELETE_LOGICAL),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "id4"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_table.put_item.call_count, len(records_config))
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, len(records_config))

    @patch("boto3.resource")
    def test_send_message_multi_create(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id1", ActionFlag.CREATE),
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id2", ActionFlag.CREATE),
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id3", ActionFlag.CREATE)
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 3)


    @patch("boto3.resource")
    def test_send_message_multi_update(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)

        records_config = [
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id1", ActionFlag.UPDATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id2", ActionFlag.UPDATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id3", ActionFlag.UPDATE)
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 3)

    @patch("boto3.resource")
    def test_send_message_multi_logical_delete(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)

        records_config = [
            RecordConfig(EventName.DELETE_LOGICAL, Operation.DELETE_LOGICAL, "delete-id1", ActionFlag.DELETE_LOGICAL),
            RecordConfig(EventName.DELETE_LOGICAL, Operation.DELETE_LOGICAL, "delete-id2", ActionFlag.DELETE_LOGICAL),
            RecordConfig(EventName.DELETE_LOGICAL, Operation.DELETE_LOGICAL, "delete-id3", ActionFlag.DELETE_LOGICAL)
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 3)

    @patch("boto3.resource")
    def test_send_message_multi_physical_delete(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)

        records_config = [
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id1"),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id2"),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id3")
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 3)

    @patch("boto3.resource")
    def test_single_error_in_multi(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)
        mock_table.put_item.side_effect = [ success_response, fail_response, success_response]

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "fail-id1.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id1.3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertFalse(result)
        self.assertEqual(mock_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 2)
        self.assertEqual(self.mock_logger_warning.call_count, 1)

    @patch("boto3.resource")
    def test_single_exception_in_multi(self, mock_boto_resource):
        # Arrange
        mock_table = self.setup_mock_dynamodb(mock_boto_resource)
        # arrange so the 3rd record fails
        mock_table.put_item.side_effect = [success_response, exception_response, success_response]

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id2.1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "exception-id2.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id2.3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertFalse(result)
        self.assertEqual(mock_table.put_item.call_count, 3)
        self.assertEqual(self.mock_firehose_logger.send_log.call_count, 2)
        self.assertEqual(self.mock_logger_exception.call_count, 1)

@patch("delta.process_record")
@patch("boto3.resource")
def test_handler_calls_process_record_for_each_event(self, mock_boto_resource, mock_process_record):
    # Arrange
    mock_delta_table = MagicMock()
    mock_boto_resource.return_value.Table.return_value = mock_delta_table

    # Create an event with 3 records
    event = {
        "Records": [
            { "a": "record1" },
            { "a": "record2" },
            { "a": "record3" }
        ]
    }
    context = {}

    # Mock process_record to always return True
    mock_process_record.return_value = True

    # Act
    result = handler(event, context)

    # Assert
    self.assertTrue(result)
    self.assertEqual(mock_process_record.call_count, len(event["Records"]))
