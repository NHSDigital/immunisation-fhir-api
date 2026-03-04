import json
import unittest
from unittest.mock import patch

import boto3
from moto import mock_aws

from mns_test_queue import send_notification_to_test_queue


@mock_aws
class TestMnsSqsQueue(unittest.TestCase):
    def setUp(self):
        self.sqs = boto3.client("sqs", region_name="eu-west-2")
        response = self.sqs.create_queue(QueueName="mns-test-notifications-int")
        self.queue_url = response["QueueUrl"]

        self.mns_payload = {
            "specversion": "1.0",
            "id": "236a1d4a-5d69-4fa9-9c7f-e72bf505aa5b",
            "source": "https://int.api.service.nhs.uk/immunisation-fhir-api",
            "type": "imms-vaccinations-1",
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

    def test_send_notification_to_queue_success(self):
        """Test successful send to SQS queue with complete payload."""
        with patch("mns_test_queue.MNS_TEST_QUEUE_URL", self.queue_url):
            send_notification_to_test_queue(self.mns_payload)

        messages = self.sqs.receive_message(
            QueueUrl=self.queue_url, MaxNumberOfMessages=1, MessageAttributeNames=["All"]
        )

        self.assertIn("Messages", messages)
        self.assertEqual(len(messages["Messages"]), 1)

        # Verify message body
        mns_payload = json.loads(messages["Messages"][0]["Body"])
        attributes = messages["Messages"][0]["MessageAttributes"]
        self.assertEqual(attributes["source"]["StringValue"], "mns-publisher-lambda")

        self.assertEqual(mns_payload["subject"], "9481152782")
        self.assertEqual(mns_payload["filtering"]["generalpractitioner"], "Y12345")
        self.assertEqual(mns_payload["filtering"]["sourceorganisation"], "B0C4P")
        self.assertEqual(mns_payload["filtering"]["sourceapplication"], "TPP")
        self.assertEqual(mns_payload["filtering"]["immunisationtype"], "HIB")
        self.assertEqual(mns_payload["filtering"]["action"], "CREATE")
        self.assertEqual(mns_payload["filtering"]["subjectage"], 21)
