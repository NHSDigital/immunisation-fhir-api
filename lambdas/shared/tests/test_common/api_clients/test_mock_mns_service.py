import json
import unittest

import boto3
from moto import mock_aws

from common.api_clients.mock_mns_service import MockMnsService


@mock_aws
class TestMockMnsService(unittest.TestCase):
    """Tests for MockMnsService (dev environment)."""

    def setUp(self):
        """Set up mocked SQS queue and test payload."""
        # Create mock SQS queue
        self.sqs = boto3.client("sqs", region_name="eu-west-2")
        response = self.sqs.create_queue(QueueName="mns-test-notifications-dev")
        self.queue_url = response["QueueUrl"]

        self.mns_payload = {
            "specversion": "1.0",
            "id": "236a1d4a-5d69-4fa9-9c7f-e72bf505aa5b",
            "source": "https://int.api.service.nhs.uk/immunisation-fhir-api",
            "type": "imms-vaccinations-2",
            "time": "20260212T174437+00:00",
            "subject": "9481152782",
            "dataref": "https://int.api.service.nhs.uk/immunisation-fhir-api/Immunization/d058014c-b0fd-4471-8db9-3316175eb825",
            "filtering": {
                "generalpractitioner": "Y12345",
                "sourceorganisation": "B0C4P",
                "sourceapplication": "TPP",
                "subjectage": 21,
                "immunisationtype": "HIB",
                "action": "CREATE",
            },
        }

    def test_publish_notification_success(self):
        """Test MockMnsService successfully publishes to SQS queue."""
        # Create mock service with queue URL
        mock_service = MockMnsService(queue_url=self.queue_url)

        # Publish notification
        mock_service.publish_notification(self.mns_payload)

        # Verify message was sent to queue
        messages = self.sqs.receive_message(
            QueueUrl=self.queue_url, MaxNumberOfMessages=1, MessageAttributeNames=["All"]
        )

        # Assert message exists
        self.assertIn("Messages", messages)
        self.assertEqual(len(messages["Messages"]), 1)

        # Verify message body
        message_body = json.loads(messages["Messages"][0]["Body"])
        self.assertEqual(message_body["id"], "236a1d4a-5d69-4fa9-9c7f-e72bf505aa5b")
        self.assertEqual(message_body["subject"], "9481152782")
        self.assertEqual(message_body["filtering"]["generalpractitioner"], "Y12345")
        self.assertEqual(message_body["filtering"]["sourceorganisation"], "B0C4P")
        self.assertEqual(message_body["filtering"]["sourceapplication"], "TPP")
        self.assertEqual(message_body["filtering"]["immunisationtype"], "HIB")
        self.assertEqual(message_body["filtering"]["action"], "CREATE")
        self.assertEqual(message_body["filtering"]["subjectage"], 21)

        # Verify message attributes
        attributes = messages["Messages"][0]["MessageAttributes"]
        self.assertEqual(attributes["source"]["StringValue"], "mns-publisher-lambda")

    def test_publish_notification_multiple_messages(self):
        """Test MockMnsService handles multiple publications."""
        mock_service = MockMnsService(queue_url=self.queue_url)

        # Publish multiple notifications
        payload1 = {**self.mns_payload, "id": "notification-1"}
        payload2 = {**self.mns_payload, "id": "notification-2"}

        mock_service.publish_notification(payload1)
        mock_service.publish_notification(payload2)

        # Verify both messages in queue
        messages = self.sqs.receive_message(QueueUrl=self.queue_url, MaxNumberOfMessages=10)

        self.assertEqual(len(messages["Messages"]), 2)

        message_ids = [json.loads(msg["Body"])["id"] for msg in messages["Messages"]]
        self.assertIn("notification-1", message_ids)
        self.assertIn("notification-2", message_ids)

    def test_publish_notification_sqs_failure(self):
        """Test MockMnsService raises exception on SQS failure."""
        # Use invalid queue URL
        mock_service = MockMnsService(queue_url="queue_url=invalid_queue_url")
        with self.assertRaises(Exception):
            mock_service.publish_notification(self.mns_payload)
