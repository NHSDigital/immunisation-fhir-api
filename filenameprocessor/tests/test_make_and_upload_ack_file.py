"""Tests for make_and_upload_ack_file functions"""

from unittest import TestCase
from unittest.mock import patch
from copy import deepcopy
from boto3 import client as boto3_client
from moto import mock_s3

from tests.utils_for_tests.utils_for_filenameprocessor_tests import get_csv_file_dict_reader
from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT, BucketNames
from tests.utils_for_tests.values_for_tests import MockFileDetails

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from make_and_upload_ack_file import make_the_ack_data, upload_ack_file, make_and_upload_the_ack_file
    from clients import REGION_NAME


s3_client = boto3_client("s3", region_name=REGION_NAME)

FILE_DETAILS = MockFileDetails.emis_flu

# NOTE: The expected ack data is the same for all scenarios as the ack file is only created if an error occurs
# or validation fails
EXPECTED_ACK_DATA = {
    "MESSAGE_HEADER_ID": FILE_DETAILS.message_id,
    "HEADER_RESPONSE_CODE": "Failure",
    "ISSUE_SEVERITY": "Fatal",
    "ISSUE_CODE": "Fatal Error",
    "ISSUE_DETAILS_CODE": "10001",
    "RESPONSE_TYPE": "Technical",
    "RESPONSE_CODE": "10002",
    "RESPONSE_DISPLAY": "Infrastructure Level Response Value - Processing Error",
    "RECEIVED_TIME": FILE_DETAILS.created_at_formatted_string,
    "MAILBOX_FROM": "",
    "LOCAL_ID": "",
    "MESSAGE_DELIVERY": False,
}


@mock_s3
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestMakeAndUploadAckFile(TestCase):
    """Tests for make_and_upload_ack_file functions"""

    def setUp(self):
        """Set up the bucket for the ack files"""
        s3_client.create_bucket(
            Bucket=BucketNames.DESTINATION, CreateBucketConfiguration={"LocationConstraint": REGION_NAME}
        )

    def test_make_ack_data(self):
        "Tests make_ack_data makes correct ack data based on the input args"
        # CASE: message not delivered (this is the only case which creates an ack file for filenameprocessor)
        self.assertEqual(
            make_the_ack_data(
                message_id=FILE_DETAILS.message_id,
                message_delivered=False,
                created_at_formatted_string=FILE_DETAILS.created_at_formatted_string,
            ),
            EXPECTED_ACK_DATA,
        )

    def test_upload_ack_file(self):
        """Test that upload_ack_file successfully uploads the ack file"""
        upload_ack_file(
            file_key=FILE_DETAILS.file_key,
            ack_data=deepcopy(EXPECTED_ACK_DATA),
            created_at_formatted_string=FILE_DETAILS.created_at_formatted_string,
        )

        expected_result = [deepcopy(EXPECTED_ACK_DATA)]
        # Note that the data downloaded from the CSV will contain the bool as a string
        expected_result[0]["MESSAGE_DELIVERY"] = "False"
        csv_dict_reader = get_csv_file_dict_reader(s3_client, BucketNames.DESTINATION, FILE_DETAILS.ack_file_key)
        self.assertEqual(list(csv_dict_reader), expected_result)

    def test_make_and_upload_ack_file(self):
        """Test that make_and_upload_ack_file uploads an ack file containing the correct values"""
        make_and_upload_the_ack_file(
            message_id=FILE_DETAILS.message_id,
            file_key=FILE_DETAILS.file_key,
            message_delivered=False,
            created_at_formatted_string=FILE_DETAILS.created_at_formatted_string,
        )

        expected_result = [deepcopy(EXPECTED_ACK_DATA)]
        # Note that the data downloaded from the CSV will contain the bool as a string
        expected_result[0]["MESSAGE_DELIVERY"] = "False"
        csv_dict_reader = get_csv_file_dict_reader(s3_client, BucketNames.DESTINATION, FILE_DETAILS.ack_file_key)
        self.assertEqual(list(csv_dict_reader), expected_result)
