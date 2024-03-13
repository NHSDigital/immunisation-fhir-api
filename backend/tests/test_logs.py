import boto3
import json
import unittest
from unittest.mock import create_autospec

from logs import SplunkLogger


class TestSplunkLogs(unittest.TestCase):
    def setUp(self):
        self.stream_name = "test-stream"
        self.client = create_autospec(boto3.client("firehose"))
        self.splunk = SplunkLogger(stream_name=self.stream_name, boto_client=self.client)

    def test_splunk_logs(self):
        """it should send json logs by put_record to firehose"""
        self.client.put_record.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        message = {"a-key": "a-value"}

        # When
        response = self.splunk.log(message)

        # Then
        expected_payload = {"Data": json.dumps(message)}
        self.client.put_record.assert_called_once_with(DeliveryStreamName=self.stream_name, Record=expected_payload)
        self.assertEqual(response, self.client.put_record.return_value)
