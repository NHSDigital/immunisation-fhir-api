"""Tests for send_sqs_message functions"""

from unittest import TestCase
from unittest.mock import patch, MagicMock
from json import loads as json_loads
from copy import deepcopy
from moto import mock_sqs
import boto3

from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT, Sqs
from tests.utils_for_tests.values_for_tests import MockFileDetails

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from send_sqs_message import send_to_supplier_queue, make_and_send_sqs_message
    from errors import UnhandledSqsError, InvalidSupplierError
    from clients import REGION_NAME

FLU_EMIS_FILE_DETAILS = MockFileDetails.emis_flu
RSV_RAVS_FILE_DETAILS = MockFileDetails.ravs_rsv_1
fake_queue_url = "https://sqs.eu-west-2.amazonaws.com/123456789012/non_existent_queue"

NON_EXISTENT_QUEUE_ERROR_MESSAGE = (
    "An unexpected error occurred whilst sending to SQS: An error occurred (AWS.SimpleQueueService.NonExistent"
    + "Queue) when calling the SendMessage operation: The specified queue does not exist for this wsdl version."
)


@mock_sqs
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestSendSQSMessage(TestCase):
    """Tests for send_sqs_message functions"""

    def setUp(self):
        self.sqs_client = boto3.client("sqs", region_name=REGION_NAME)
        self.queue_url = self.sqs_client.create_queue(
            QueueName=Sqs.QUEUE_NAME, Attributes=Sqs.ATTRIBUTES
        )["QueueUrl"]

    def test_send_to_supplier_queue_success(self):
        """Test send_to_supplier_queue function for a successful message send"""
        flu_emis_1 = deepcopy(FLU_EMIS_FILE_DETAILS)
        flu_emis_2 = deepcopy(FLU_EMIS_FILE_DETAILS)
        flu_emis_2.sqs_message_body["message_id"] = "flu_emis_test_id_2"
        rsv_ravs_1 = deepcopy(RSV_RAVS_FILE_DETAILS)

        with patch.dict("os.environ", {"QUEUE_URL": self.queue_url}):
            with patch("send_sqs_message.sqs_client", self.sqs_client):
                for file_details in [flu_emis_1, rsv_ravs_1, flu_emis_2]:
                    self.assertIsNone(
                        send_to_supplier_queue(
                        message_body=deepcopy(file_details.sqs_message_body),
                        vaccine_type=file_details.vaccine_type,
                        supplier=file_details.supplier,
                    )
                )

            # Verify messages in queue
            messages = self.sqs_client.receive_message(
                QueueUrl=self.queue_url, MaxNumberOfMessages=10, AttributeNames=["All"]
            )["Messages"]

            self.assertEqual(len(messages), 3)
            self.assertEqual(json_loads(messages[0]["Body"]), flu_emis_1.sqs_message_body)
            self.assertEqual(messages[0]["Attributes"]["MessageGroupId"], flu_emis_1.queue_name)
            self.assertEqual(json_loads(messages[1]["Body"]), rsv_ravs_1.sqs_message_body)
            self.assertEqual(messages[1]["Attributes"]["MessageGroupId"], rsv_ravs_1.queue_name)
            self.assertEqual(json_loads(messages[2]["Body"]), flu_emis_2.sqs_message_body)
            self.assertEqual(messages[2]["Attributes"]["MessageGroupId"], flu_emis_2.queue_name)

    def test_send_to_supplier_queue_failure_due_to_queue_does_not_exist(self):
        """Test send_to_supplier_queue function for a failed message send due to queue not existing"""

        with patch.dict("os.environ", {"QUEUE_URL": fake_queue_url}):
            with patch("send_sqs_message.sqs_client", self.sqs_client):
                with self.assertRaises(UnhandledSqsError) as context:
                 send_to_supplier_queue(
                message_body=deepcopy(FLU_EMIS_FILE_DETAILS.sqs_message_body),
                vaccine_type=FLU_EMIS_FILE_DETAILS.vaccine_type,
                supplier=FLU_EMIS_FILE_DETAILS.supplier,
            )
        self.assertIn("An unexpected error occurred whilst sending to SQS", str(context.exception))
        self.assertTrue(
            "Queue does not exist" in str(context.exception) or "NonExistentQueue" in str(context.exception)
        )

    def test_send_to_supplier_queue_failure_due_to_absent_supplier_or_vaccine_type(self):
        """Test send_to_supplier_queue function for a failed message send"""
        # Set up the sqs_queue
        self.sqs_client.create_queue(QueueName=Sqs.QUEUE_NAME, Attributes=Sqs.ATTRIBUTES)
        expected_error_message = (
            "Message not sent to supplier queue as unable to identify supplier and/ or vaccine type"
        )

        keys_to_set_to_empty = ["supplier", "vaccine_type"]
        for key_to_set_to_empty in keys_to_set_to_empty:
            with self.subTest(f"{key_to_set_to_empty} set to empty string"):
                mock_sqs_client = MagicMock()
                with patch("send_sqs_message.sqs_client", mock_sqs_client):
                    with self.assertRaises(InvalidSupplierError) as context:
                        message_body = {**FLU_EMIS_FILE_DETAILS.sqs_message_body, key_to_set_to_empty: ""}
                        vaccine_type = message_body["vaccine_type"]
                        supplier = message_body["supplier"]
                        send_to_supplier_queue(message_body, supplier, vaccine_type)
                self.assertEqual(str(context.exception), expected_error_message)
                mock_sqs_client.send_message.assert_not_called()

    def test_make_and_send_sqs_message_success(self):
        """Test make_and_send_sqs_message function for a successful message send"""
        # Create a mock SQS queue
        queue_url = self.sqs_client.create_queue(QueueName=Sqs.QUEUE_NAME, Attributes=Sqs.ATTRIBUTES)["QueueUrl"]

        # Call the send_to_supplier_queue function
        with patch.dict("os.environ", {"QUEUE_URL": queue_url}):
            with patch("send_sqs_message.sqs_client", self.sqs_client):
                self.assertIsNone(
                    make_and_send_sqs_message(
                        file_key=FLU_EMIS_FILE_DETAILS.file_key,
                        message_id=FLU_EMIS_FILE_DETAILS.message_id,
                        permission=deepcopy(FLU_EMIS_FILE_DETAILS.permissions_list),
                        vaccine_type=FLU_EMIS_FILE_DETAILS.vaccine_type,
                        supplier=FLU_EMIS_FILE_DETAILS.supplier,
                        created_at_formatted_string=FLU_EMIS_FILE_DETAILS.created_at_formatted_string,
                )
        )
            # Assert that correct message has reached the queue
            messages = self.sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
            self.assertEqual(json_loads(messages["Messages"][0]["Body"]), deepcopy(FLU_EMIS_FILE_DETAILS.sqs_message_body))

    def test_make_and_send_sqs_message_failure(self):
        
        with patch.dict("os.environ", {"QUEUE_URL": fake_queue_url}):
            with patch("send_sqs_message.sqs_client", boto3.client("sqs", region_name=REGION_NAME)):
                with self.assertRaises(UnhandledSqsError) as context:
                    make_and_send_sqs_message(
                        file_key=FLU_EMIS_FILE_DETAILS.file_key,
                        message_id=FLU_EMIS_FILE_DETAILS.message_id,
                        permission=deepcopy(FLU_EMIS_FILE_DETAILS.permissions_list),
                        vaccine_type=FLU_EMIS_FILE_DETAILS.vaccine_type,
                        supplier=FLU_EMIS_FILE_DETAILS.supplier,
                        created_at_formatted_string=FLU_EMIS_FILE_DETAILS.created_at_formatted_string,
                    )
        self.assertIn(NON_EXISTENT_QUEUE_ERROR_MESSAGE, str(context.exception))
