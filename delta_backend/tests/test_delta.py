import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
import os
from sample_data.test_resource_data import get_test_data_resource
import json


mock_queue = "https://sqs.us-east-1.amazonaws.com/123456789012/MyQueue"
MOCK_ENV_VARS = {
    "AWS_SQS_QUEUE_URL": mock_queue,
    "DELTA_TABLE_NAME" : "my_delta_table",
    "SOURCE" : "my_source"
}
with patch.dict("os.environ", MOCK_ENV_VARS):
    from delta import send_message, handler  # Import after setting environment variables


@patch.dict("os.environ", MOCK_ENV_VARS, clear=True)
class DeltaTestCase(unittest.TestCase):

    def setUp(self):
        # Common setup if needed
        self.context = {}
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.firehose_logger_patcher = patch("delta.firehose_logger")
        self.mock_firehose_logger = self.firehose_logger_patcher.start()
        # self.mock_firehose_logger.send_log = MagicMock()


    def tearDown(self):
        self.logger_exception_patcher.stop()
        self.logger_info_patcher.stop()
        self.mock_firehose_logger.stop()

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

    @staticmethod
    def get_event(event_name="INSERT", operation="CREATE", supplier="EMIS", n_records=1):
        """Create test event for the handler function."""
        return {
            "Records": [
                DeltaTestCase.get_event_record(f"covid#{i+1}2345", event_name, operation, supplier)
                for i in range(n_records)
            ]
        }

    @staticmethod
    def get_event_record(pk, event_name="INSERT", operation="CREATE", supplier="EMIS"):
        if operation != "DELETE":
            return{
                "eventName": event_name,
                "dynamodb": {
                    "ApproximateCreationDateTime": 1690896000,
                    "NewImage": {
                        "PK": {"S": pk},
                        "PatientSK": {"S": pk},
                        "IdentifierPK": {"S": "system#1"},
                        "Operation": {"S": operation},
                        "SupplierSystem": {"S": supplier},
                        "Resource": {
                            "S": json.dumps(get_test_data_resource()),
                        },
                    },
                },
            }
        else:
            return {
                "eventName": "REMOVE",
                "dynamodb": {
                    "ApproximateCreationDateTime": 1690896000,
                    "Keys": {
                        "PK": {"S": pk},
                        "PatientSK": {"S": pk},
                        "SupplierSystem": {"S": "EMIS"},
                        "Resource": {
                            "S": json.dumps(get_test_data_resource()),
                        },
                    },
                },
            }

    @patch("boto3.client")
    def test_send_message_success(self, mock_boto_client):
        # Arrange
        mock_sqs = self.setup_mock_sqs(mock_boto_client)
        record = {"key": "value"}

        # Act
        send_message(record)

        # Assert
        mock_sqs.send_message.assert_called_once_with(
            QueueUrl=mock_queue, MessageBody=json.dumps(record)
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
        self.setup_mock_dynamodb(mock_boto_resource)
        suppilers = ["DPS", "EMIS"]
        for supplier in suppilers:
            event = self.get_event(supplier=supplier)

            # Act
            result = handler(event, self.context)

            # Assert
            self.assertEqual(result["statusCode"], 200)

    @patch("boto3.resource")
    def test_handler_failure(self, mock_boto_resource):
        # Arrange
        self.setup_mock_dynamodb(mock_boto_resource, status_code=500)
        event = self.get_event()

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertEqual(result["statusCode"], 500)

    @patch("boto3.resource")
    def test_handler_success_update(self, mock_boto_resource):
        # Arrange
        self.setup_mock_dynamodb(mock_boto_resource)
        event = self.get_event(event_name="UPDATE", operation="UPDATE")

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertEqual(result["statusCode"], 200)

    @patch("boto3.resource")
    def test_handler_success_remove(self, mock_boto_resource):
        # Arrange
        self.setup_mock_dynamodb(mock_boto_resource)
        event = self.get_event(event_name="REMOVE", operation="DELETE")

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertEqual(result["statusCode"], 200)

    @patch("boto3.resource")
    @patch("boto3.client")
    def test_handler_exception_intrusion_check(self, mock_boto_resource, mock_boto_client):
        # Arrange
        self.setup_mock_dynamodb(mock_boto_resource, status_code=500)
        mock_boto_client.return_value = MagicMock()
        event = self.get_event()

        # Act & Assert

        result = handler(event, self.context)
        self.assertEqual(result["statusCode"], 500)

    @patch("boto3.resource")
    @patch("boto3.client")
    def test_handler_exception_intrusion(self, mock_boto_client, mock_boto_resource):
        # Arrange
        self.setUp_mock_resources(mock_boto_resource, mock_boto_client)

        event = self.get_event()
        context = {}

        # Act & Assert
        with self.assertRaises(Exception):
            handler(event, context)

        self.mock_logger_exception.assert_called_once_with("Delta Lambda failure: Test Exception")

    @patch("boto3.resource")
    @patch("delta.handler")
    def test_handler_exception_intrusion_check_false(self, mocked_intrusion, mock_boto_client):
        # Arrange
        self.setUp_mock_resources(mocked_intrusion, mock_boto_client)
        event = self.get_event()
        context = {}

        # Act & Assert
        with self.assertRaises(Exception):
            handler(event, context)

    @patch("delta.logger.info")  # Mock logging
    def test_dps_record_skipped(self, mock_logger_info):

        event = self.get_event(supplier="DPSFULL")
        context = {}

        response = handler(event, context)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"], "Record from DPS skipped for 12345")

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

        event = self.get_event()
        context = {}

        response = handler(event, context)

        # self.assertEqual(response["statusCode"], 207)
        # self.assertIn("Partial success", response["body"])

        # Check logging and Firehose were called
        # mock_logger_info.assert_called()
        # mock_firehose_send_log.assert_called()
