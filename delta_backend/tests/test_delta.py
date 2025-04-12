import unittest
import os
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from sample_data.test_resource_data import get_test_data_resource

# Set environment variables before importing the module
os.environ["AWS_SQS_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/123456789012/MyQueue"
os.environ["DELTA_TABLE_NAME"] = "my_delta_table"
os.environ["SOURCE"] = "my_source"
os.environ["SPLUNK_FIREHOSE_NAME"] = "my_firehose"

from src.delta import send_message, handler  # Import after setting environment variables
import json


class DeltaTestCase(unittest.TestCase):

    def setUp(self):
        # Common setup if needed
        self.context = {}

    @patch("delta.firehose_logger")
    @patch("boto3.client") 
    @patch("delta.boto3.resource")
    def test_handler(self, mock_boto_resource, mock_boto_client, mock_firehose_logger):
        # Arrange
        event = { "text": "hello world"}

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertEqual(result["statusCode"], 200)
