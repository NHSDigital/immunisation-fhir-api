import unittest
from unittest.mock import patch, MagicMock
import json
from botocore.exceptions import ClientError
from helpers.sqs_utils import send_message

class TestSqsUtils(unittest.TestCase):

    @staticmethod
    def setup_mock_sqs(mock_boto_client, return_value={"ResponseMetadata": {"HTTPStatusCode": 200}}):
        mock_sqs = mock_boto_client.return_value
        mock_sqs.send_message.return_value = return_value
        return mock_sqs

    @patch("boto3.client")
    def test_send_message_success(self, mock_boto_client):
        # Arrange
        mock_sqs = self.setup_mock_sqs(mock_boto_client)
        record = {"key": "value"}
        sqs_queue_url = "sqs_queue_url"

        # Act
        send_message(record, sqs_queue_url)

        # Assert
        mock_sqs.send_message.assert_called_once_with(
            QueueUrl=sqs_queue_url, MessageBody=json.dumps(record)
        )

    @patch("boto3.client")
    @patch("logging.Logger.error")
    def test_send_message_client_error(self, mock_logger_error, mock_boto_client):
        # Arrange
        mock_sqs = MagicMock()
        mock_boto_client.return_value = mock_sqs
        record = {"key": "value"}
        sqs_queue_url = "sqs_queue_url"
 
        # Simulate ClientError
        error_response = {"Error": {"Code": "500", "Message": "Internal Server Error"}}
        mock_sqs.send_message.side_effect = ClientError(error_response, "SendMessage")

        # Act
        send_message(record, sqs_queue_url)

        # Assert
        mock_logger_error.assert_called_once_with(
            f"Error sending record to DLQ: An error occurred (500) when calling the SendMessage operation: Internal Server Error"
        )