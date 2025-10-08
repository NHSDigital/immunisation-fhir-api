import unittest
from common.aws_lambda_event import AwsEventType
from common.s3_event import S3Event


class TestS3Event(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.s3_record_dict = {
            "eventVersion": "2.1",
            "eventSource": "aws:s3",
            "awsRegion": "us-west-2",
            "eventTime": "1970-01-01T00:00:00.000Z",
            "eventName": "ObjectCreated:Put",
            "userIdentity": {"principalId": "my-example-user"},
            "requestParameters": {"sourceIPAddress": "172.16.0.1"},
            "responseElements": {
                "x-amz-request-id": "C3D13FE58DE4C810",
                "x-amz-id-2": "FMyUVURIY8/IgAtTv8xRjskZQpcIZ9KG4V5Wp6S7S/JRWeUWerMUE5JgHvANOjpD",
            },
            "s3": {
                "s3SchemaVersion": "1.0",
                "configurationId": "my-test-config",
                "bucket": {
                    "name": "my-test-bucket",
                    "ownerIdentity": {"principalId": "my-example-id"},
                    "arn": "arn:aws:s3:::my-test-bucket",
                },
                "object": {
                    "key": "my-test-key.csv",
                    "size": 1024,
                    "eTag": "d41d8cd98f00b204e9800998ecf8427e",
                    "versionId": "096fKKXTRTtl3on89fVO.nfljtsv6qko",
                    "sequencer": "0055AED6DCD90281E5",
                },
            },
        }

    def test_s3_event(self):
        """Test initialization with S3 event"""
        event = {"Records": [self.s3_record_dict], "eventSource": "aws:s3"}

        s3_event = S3Event(event)

        self.assertEqual(s3_event.event_type, AwsEventType.S3)
        self.assertEqual(len(s3_event.records), 1)

        s3_records = s3_event.get_s3_records()
        self.assertEqual(len(s3_records), 1)
        self.assertEqual(s3_records[0].get_bucket_name(), "my-test-bucket")
        self.assertEqual(s3_records[0].get_object_key(), "my-test-key.csv")

    def test_s3_event_with_multiple_records(self):
        """Test initialization with multiple s3 records"""
        s3_record_2 = self.s3_record_dict.copy()
        s3_record_2["s3"]["bucket"]["name"] = "my-second-test-bucket"

        event = {"Records": [self.s3_record_dict, s3_record_2], "eventSource": "aws:s3"}

        s3_event = S3Event(event)

        self.assertEqual(s3_event.event_type, AwsEventType.S3)
        self.assertEqual(len(s3_event.records), 2)

        s3_records = s3_event.get_s3_records()
        self.assertEqual(len(s3_records), 2)
        self.assertEqual(s3_records[1].get_bucket_name(), "my-second-test-bucket")

    def test_s3_event_with_no_records(self):
        """Test initialization with no s3 records"""
        event = {"Records": [], "eventSource": "aws:s3"}

        s3_event = S3Event(event)

        self.assertEqual(s3_event.event_type, AwsEventType.S3)
        self.assertEqual(len(s3_event.records), 0)

        s3_records = s3_event.get_s3_records()
        self.assertEqual(len(s3_records), 0)
