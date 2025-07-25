import unittest
from common.aws_lambda_event import AwsLambdaEvent, AwsEventType


class TestAwsLambdaEvent(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.sqs_record_dict = {
            'messageId': '12345-abcde-67890',
            'receiptHandle': 'AQEBwJnKyrHigUMZj6rYigCgxlaS3SLy0a...',
            'body': '{"key": "value"}',
            'attributes': {
                'ApproximateReceiveCount': '1',
                'SentTimestamp': '1545082649183'
            },
            'messageAttributes': {},
            'md5OfBody': 'e4e68fb7bd0e697a0ae8f1bb342846b3',
            'eventSource': 'aws:sqs',
            'eventSourceARN': 'arn:aws:sqs:us-east-1:123456789012:my-queue',
            'awsRegion': 'us-east-1'
        }

    def test_init_with_sqs_event(self):
        """Test initialization with SQS event"""
        event = {
            'Records': [self.sqs_record_dict],
            'eventSource': 'aws:sqs'
        }

        lambda_event = AwsLambdaEvent(event)

        self.assertEqual(lambda_event.event_type, AwsEventType.SQS)
        self.assertEqual(len(lambda_event.records), 1)
        self.assertEqual(lambda_event.records[0]['messageId'], '12345-abcde-67890')

    def test_init_with_multiple_sqs_records(self):
        """Test initialization with multiple SQS records"""
        sqs_record_2 = self.sqs_record_dict.copy()
        sqs_record_2['messageId'] = 'second-message-id'

        event = {
            'Records': [self.sqs_record_dict, sqs_record_2],
            'eventSource': 'aws:sqs'
        }

        lambda_event = AwsLambdaEvent(event)

        self.assertEqual(lambda_event.event_type, AwsEventType.SQS)
        self.assertEqual(len(lambda_event.records), 2)
        self.assertEqual(lambda_event.records[0]['messageId'], '12345-abcde-67890')
        self.assertEqual(lambda_event.records[1]['messageId'], 'second-message-id')

    def test_init_with_empty_records(self):
        """Test initialization with empty records array"""
        event = {
            'Records': []
        }

        lambda_event = AwsLambdaEvent(event)

        self.assertEqual(lambda_event.event_type, AwsEventType.UNKNOWN)
        self.assertEqual(len(lambda_event.records), 0)

    def test_init_without_records(self):
        """Test initialization without Records key"""
        event = {
            'some_other_key': 'value'
        }

        lambda_event = AwsLambdaEvent(event)

        self.assertEqual(lambda_event.event_type, AwsEventType.UNKNOWN)
        self.assertEqual(len(lambda_event.records), 0)

    def test_init_with_unknown_event_source(self):
        """Test initialization with unknown event source"""
        unknown_record = {
            'eventSource': 'aws:unknown-service',
            'data': 'test'
        }
        event = {
            'Records': [unknown_record]
        }

        lambda_event = AwsLambdaEvent(event)

        self.assertEqual(lambda_event.event_type, AwsEventType.UNKNOWN)
        self.assertEqual(len(lambda_event.records), 1)

    def test_init_with_missing_event_source(self):
        """Test initialization with record missing eventSource"""
        record_without_source = {
            'messageId': 'test-id',
            'body': 'test'
        }
        event = {
            'Records': [record_without_source]
        }

        lambda_event = AwsLambdaEvent(event)

        self.assertEqual(lambda_event.event_type, AwsEventType.UNKNOWN)

    def test_enum_values(self):
        """Test AwsEventType enum values"""
        self.assertEqual(AwsEventType.SQS.value, "aws:sqs")
        self.assertEqual(AwsEventType.S3.value, "aws:s3")
        self.assertEqual(AwsEventType.SNS.value, "aws:sns")
        self.assertEqual(AwsEventType.UNKNOWN.value, "unknown")

    def test_mixed_multiple_records(self):
        """Test that mixed event sources uses the first record's type"""
        mixed_records = [self.sqs_record_dict, {}]
        event = {'Records': mixed_records, 'eventSource': 'aws:sqs'}

        lambda_event = AwsLambdaEvent(event)

        self.assertEqual(lambda_event.event_type, AwsEventType.SQS)
        self.assertEqual(len(lambda_event.records), 2)

    def test_empty_records(self):
        """Test empty records"""
        event = {'Records': []}

        lambda_event = AwsLambdaEvent(event)

        self.assertEqual(lambda_event.event_type, AwsEventType.UNKNOWN)
        self.assertEqual(len(lambda_event.records), 0)
