import unittest
from unittest.mock import patch, MagicMock
import json
from src.log_firehose import FirehoseLogger


class TestFirehoseLogger(unittest.TestCase):

    @patch("boto3.client")
    def test_send_log(self, mock_boto_client):
        """it should send log message to Firehose"""

        # Arrange
        mock_response = {
            "RecordId": "shardId-000000000000000000000001",
            "ResponseMetadata": {
            "RequestId": "12345abcde67890fghijk",
            "HTTPStatusCode": 200, 
            "RetryAttempts": 0
            }
        }        
        mock_firehose_client = MagicMock()
        mock_boto_client.return_value = mock_firehose_client
        mock_firehose_client.put_record.return_value = mock_response
        
        stream_name = "stream_name"
        firehose_logger = FirehoseLogger(boto_client=mock_firehose_client, stream_name=stream_name)    
        log_message = {"text": "Test log message"}

        # Act
        firehose_logger.send_log(log_message)

        # Assert
        mock_firehose_client.put_record.assert_called_once()
        self.assertEqual(mock_firehose_client.put_record.return_value, mock_response)

    @patch("boto3.client")
    def test_send_log_failure(self, mock_boto_client):
        """Test that send_log logs an exception when put_record fails."""

        # Arrange
        mock_firehose_client = MagicMock()
        mock_boto_client.return_value = mock_firehose_client
        mock_firehose_client.put_record.side_effect = Exception("Test exception")

        stream_name = "test-stream"
        firehose_logger = FirehoseLogger(boto_client=mock_firehose_client, stream_name=stream_name)
        log_message = {"key": "value"}

        with patch("src.log_firehose.logger.exception") as mock_logger_exception:
            # Act
            firehose_logger.send_log(log_message)

            # Assert
            mock_firehose_client.put_record.assert_called_once_with(
                DeliveryStreamName="test-stream",
                Record={"Data": json.dumps(log_message).encode("utf-8")},
            )
            mock_logger_exception.assert_called_once_with("Error sending log to Firehose: Test exception")

if __name__ == "__main__":
    unittest.main()
