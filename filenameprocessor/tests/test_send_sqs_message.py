"""Tests for send_sqs_message functions"""

from unittest import TestCase
from unittest.mock import patch, MagicMock
from json import loads as json_loads
from copy import deepcopy
from moto import mock_sqs
from boto3 import client as boto3_client
from send_sqs_message import send_to_supplier_queue, make_and_send_sqs_message
from errors import UnhandledSqsError, InvalidSupplierError
from clients import REGION_NAME
from tests.utils_for_tests.values_for_tests import MOCK_ENVIRONMENT_DICT, MockFileDetails, Sqs

sqs_client = boto3_client("sqs", region_name=REGION_NAME)

FILE_DETAILS = MockFileDetails.flu_emis


@mock_sqs
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestSendSQSMessage(TestCase):
    """Tests for send_sqs_message functions"""

    def test_send_to_supplier_queue_success(self):
        """Test send_to_supplier_queue function for a successful message send"""
        # Set up the sqs_queue
        queue_url = sqs_client.create_queue(QueueName=Sqs.QUEUE_NAME, Attributes=Sqs.ATTRIBUTES)["QueueUrl"]

        self.assertIsNone(send_to_supplier_queue(deepcopy(FILE_DETAILS.sqs_message_body)))

        # Assert that correct message has reached the queue
        messages = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        self.assertEqual(json_loads(messages["Messages"][0]["Body"]), FILE_DETAILS.sqs_message_body)

    def test_send_to_supplier_queue_failure_due_to_queue_does_not_exist(self):
        """Test send_to_supplier_queue function for a failed message send due to queue not existing"""
        with self.assertRaises(UnhandledSqsError) as context:
            send_to_supplier_queue(deepcopy(FILE_DETAILS.sqs_message_body))
        self.assertIn("An unexpected error occurred whilst sending to SQS", str(context.exception))

    def test_send_to_supplier_queue_failure_due_to_absent_supplier(self):
        """Test send_to_supplier_queue function for a failed message send"""
        mock_sqs_client = boto3_client("sqs", region_name=REGION_NAME)
        mock_sqs_client.send_message = MagicMock()
        mock_sqs_client.create_queue(QueueName=Sqs.QUEUE_NAME, Attributes=Sqs.ATTRIBUTES)

        with patch("send_sqs_message.sqs_client", mock_sqs_client):
            with self.assertRaises(InvalidSupplierError) as context:
                message_body = deepcopy(FILE_DETAILS.sqs_message_body)
                message_body["supplier"] = ""
                send_to_supplier_queue(message_body)

        self.assertEqual(str(context.exception), "Message not sent to supplier queue as unable to identify supplier")
        mock_sqs_client.send_message.assert_not_called()

    def test_make_and_send_sqs_message_success(self):
        """Test make_and_send_sqs_message function for a successful message send"""
        # Create a mock SQS queue
        queue_url = sqs_client.create_queue(QueueName=Sqs.QUEUE_NAME, Attributes=Sqs.ATTRIBUTES)["QueueUrl"]

        # Call the send_to_supplier_queue function
        self.assertIsNone(
            make_and_send_sqs_message(
                file_key=FILE_DETAILS.file_key,
                message_id=FILE_DETAILS.message_id,
                permission=deepcopy(FILE_DETAILS.permissions_list),
                vaccine_type=FILE_DETAILS.vaccine_type,
                supplier=FILE_DETAILS.supplier,
                created_at_formatted_string=FILE_DETAILS.created_at_formatted_string,
            )
        )

        # Assert that correct message has reached the queue
        messages = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        self.assertEqual(json_loads(messages["Messages"][0]["Body"]), deepcopy(FILE_DETAILS.sqs_message_body))

    def test_make_and_send_sqs_message_failure(self):
        """Test make_and_send_sqs_message function for a failure due to queue not existing"""
        with self.assertRaises(UnhandledSqsError) as context:
            make_and_send_sqs_message(
                file_key=FILE_DETAILS,
                message_id=FILE_DETAILS.message_id,
                permission=deepcopy(FILE_DETAILS.permissions_list),
                vaccine_type=FILE_DETAILS.vaccine_type,
                supplier=FILE_DETAILS.supplier,
                created_at_formatted_string=FILE_DETAILS.created_at_formatted_string,
            )
        self.assertIn("An unexpected error occurred whilst sending to SQS", str(context.exception))
