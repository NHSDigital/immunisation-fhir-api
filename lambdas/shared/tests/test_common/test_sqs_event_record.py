import unittest
from common.sqs_event_record import SQSEventRecord


class TestSQSEventRecord(unittest.TestCase):

    def setUp(self):
        self.sample_dict = {
            "messageId": "abc-123",
            "receiptHandle": "handle-xyz",
            "body": "{\"foo\": \"bar\"}",
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
            "awsRegion": "us-east-1"
        }

    def test_from_dict_creates_instance_correctly(self):
        record = SQSEventRecord.from_dict(self.sample_dict)

        self.assertEqual(record.message_id, "abc-123")
        self.assertEqual(record.receipt_handle, "handle-xyz")
        self.assertEqual(record.body, "{\"foo\": \"bar\"}")
        self.assertEqual(record.attributes["ApproximateReceiveCount"], "1")
        self.assertEqual(record.message_attributes["CustomAttr"]["stringValue"], "hello")
        self.assertEqual(record.md5_of_body, "abc123md5")
        self.assertEqual(record.event_source, "aws:sqs")
        self.assertEqual(record.event_source_arn, "arn:aws:sqs:us-east-1:123456789012:MyQueue")
        self.assertEqual(record.aws_region, "us-east-1")

    def test_repr(self):
        record = SQSEventRecord.from_dict(self.sample_dict)
        self.assertIn("abc-123", repr(record))
        self.assertTrue(repr(record).startswith("<SQSEventRecord"))

    def test_initialization(self):
        record = SQSEventRecord(
            message_id="test-id",
            receipt_handle="test-handle",
            body="{}",
            attributes={},
            message_attributes={},
            md5_of_body="test-md5",
            event_source="aws:sqs",
            event_source_arn="my-arn",
            aws_region="us-east-1"
        )
        self.assertEqual(record.message_id, "test-id")
        self.assertEqual(record.receipt_handle, "test-handle")
        self.assertEqual(record.body, "{}")
        self.assertEqual(record.attributes, {})
        self.assertEqual(record.message_attributes, {})
        self.assertEqual(record.md5_of_body, "test-md5")
        self.assertEqual(record.event_source, "aws:sqs")
        self.assertEqual(record.event_source_arn, "my-arn")
        self.assertEqual(record.aws_region, "us-east-1")


if __name__ == '__main__':
    unittest.main()
