import unittest
from unittest.mock import patch, MagicMock
from aws.sqs_event import SQSEvent


class TestSQSEvent(unittest.TestCase):

    def setUp(self):
        self.sample_event = {
            "Records": [
                {
                    "messageId": "abc-123",
                    "receiptHandle": "SomeHandle",
                    "body": "{\"foo\": \"bar\"}",
                    "attributes": {},
                    "messageAttributes": {},
                    "md5OfBody": "dummyhash",
                    "eventSource": "aws:sqs",
                    "eventSourceARN": "arn:aws:sqs:region:acct:queue",
                    "awsRegion": "us-east-1"
                }
            ]
        }

    @patch('sqs_event.SQSEventRecord')
    def test_from_event_creates_correct_number_of_records(self, mock_record_class):
        # Arrange
        mock_record_instance = MagicMock()
        mock_record_class.from_dict.return_value = mock_record_instance

        # Act
        event = SQSEvent.from_event(self.sample_event)

        # Assert
        self.assertEqual(len(event.records), 1)
        self.assertIs(event.records[0], mock_record_instance)
        mock_record_class.from_dict.assert_called_once_with(self.sample_event["Records"][0])

    @patch('sqs_event.SQSEventRecord')
    def test_from_event_handles_empty_records(self, mock_record_class):
        # Act
        event = SQSEvent.from_event({"Records": []})

        # Assert
        self.assertEqual(len(event.records), 0)
        mock_record_class.from_dict.assert_not_called()

    def test_repr(self):
        # Simulate a dummy record object
        dummy_event = SQSEvent(records=["fake_record_1", "fake_record_2"])
        repr_str = repr(dummy_event)
        self.assertIn("SQSEvent", repr_str)
        self.assertIn("records=2", repr_str)


if __name__ == '__main__':
    unittest.main()
