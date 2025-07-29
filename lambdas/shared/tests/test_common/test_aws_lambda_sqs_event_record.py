import unittest
from common.aws_lambda_sqs_event_record import AwsLambdaSqsEventRecord


class TestAwsLambdaSqsEventRecord(unittest.TestCase):

    def setUp(self):
        self.region = "test-region"
        self.message_id = "test-message-id"
        self.body = "{\"a\": \"b\"}"
        self.md5OfBody = "abc123md5"
        self.eventSource = "aws:sqs"
        self.test_event = {
            "messageId": self.message_id,
            "receiptHandle": "handle-xyz",
            "body": self.body,
            "attributes": {
                "ApproximateReceiveCount": "1"
            },
            "messageAttributes": {
                "CustomAttr": {
                    "stringValue": "hello",
                    "dataType": "String"
                }
            },
            "md5OfBody": "abc123md5",
            "eventSource": "aws:sqs",
            "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:MyQueue",
            "awsRegion": self.region
        }

    def test_initialisation(self):
        record = AwsLambdaSqsEventRecord(self.test_event)

        self.assertEqual(record.message_id, self.message_id)
        self.assertEqual(record.receipt_handle, "handle-xyz")
        self.assertEqual(record.body, self.body)
        self.assertEqual(record.attributes["ApproximateReceiveCount"], "1")
        self.assertEqual(record.message_attributes["CustomAttr"]["stringValue"], "hello")
        self.assertEqual(record.md5_of_body, self.md5OfBody)
        self.assertEqual(record.event_source, self.eventSource)
        self.assertEqual(record.event_source_arn, "arn:aws:sqs:us-east-1:123456789012:MyQueue")
        self.assertEqual(record.aws_region, self.region)
