import unittest
from unittest.mock import patch, MagicMock
import os
import json
from src.log_firehose import FirehoseLogger  # Assuming your FirehoseLogger class is in the log_firehose.py file.
import logging

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")


class TestFirehoseLogger(unittest.TestCase):

    @patch("boto3.client")
    def test_send_log(self, mock_boto_client):
        """it should send log message to Firehose"""

        logger.info("Test FirehoseLogger.send_log")
        
        # Create a mock boto3 client and mock the put_record response
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

        # Call the send_log method
        firehose_logger.send_log(log_message)

        # Assert that put_record was called exactly once with the correct parameters
        mock_firehose_client.put_record.assert_called_once()

        # Assert that the return value is as expected (optional)
        self.assertEqual(mock_firehose_client.put_record.return_value, mock_response)

if __name__ == "__main__":
    unittest.main()
