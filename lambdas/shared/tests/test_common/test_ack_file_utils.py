"""Tests for make_and_upload_ack_file functions"""

import unittest
from copy import deepcopy
from unittest.mock import patch

from boto3 import client as boto3_client
from moto import mock_aws

from test_common.testing_utils.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    BucketNames,
)
from test_common.testing_utils.utils_for_ack_file_tests import (
    get_csv_file_dict_reader,
)
from test_common.testing_utils.values_for_ack_file_tests import (
    MockFileDetails,
)

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.ack_file_utils import (
        make_ack_data,
        make_and_upload_ack_file,
        upload_ack_file,
    )
    from common.clients import REGION_NAME

from test_common.testing_utils.utils_for_ack_file_tests import (
    GenericSetUp,
    GenericTearDown,
)

FILE_DETAILS = MockFileDetails.flu_emis


@mock_aws
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestMakeAndUploadAckFile(unittest.TestCase):
    "Tests for make_and_upload_ack_file functions"

    def setUp(self) -> None:
        self.message_id = "test_id"
        self.created_at_formatted_string = "20211120T12000000"
        self.ack_data_validation_passed_and_message_delivered = {
            "MESSAGE_HEADER_ID": self.message_id,
            "HEADER_RESPONSE_CODE": "Success",
            "ISSUE_SEVERITY": "Information",
            "ISSUE_CODE": "OK",
            "ISSUE_DETAILS_CODE": "20013",
            "RESPONSE_TYPE": "Technical",
            "RESPONSE_CODE": "20013",
            "RESPONSE_DISPLAY": "Success",
            "RECEIVED_TIME": self.created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": "",
            "MESSAGE_DELIVERY": True,
        }
        self.ack_data_validation_passed_and_message_not_delivered = {
            "MESSAGE_HEADER_ID": self.message_id,
            "HEADER_RESPONSE_CODE": "Failure",
            "ISSUE_SEVERITY": "Information",
            "ISSUE_CODE": "OK",
            "ISSUE_DETAILS_CODE": "20013",
            "RESPONSE_TYPE": "Technical",
            "RESPONSE_CODE": "10002",
            "RESPONSE_DISPLAY": "Infrastructure Level Response Value - Processing Error",
            "RECEIVED_TIME": self.created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": "",
            "MESSAGE_DELIVERY": False,
        }
        self.ack_data_validation_failed = {
            "MESSAGE_HEADER_ID": self.message_id,
            "HEADER_RESPONSE_CODE": "Failure",
            "ISSUE_SEVERITY": "Fatal",
            "ISSUE_CODE": "Fatal Error",
            "ISSUE_DETAILS_CODE": "10001",
            "RESPONSE_TYPE": "Technical",
            "RESPONSE_CODE": "10002",
            "RESPONSE_DISPLAY": "Infrastructure Level Response Value - Processing Error",
            "RECEIVED_TIME": self.created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": "",
            "MESSAGE_DELIVERY": False,
        }

        self.s3_client = boto3_client("s3", region_name=REGION_NAME)
        GenericSetUp(self.s3_client)

    def tearDown(self):
        GenericTearDown(self.s3_client)

    def test_make_ack_data(self):
        "Tests make_ack_data makes correct ack data based on the input args"
        # Test case tuples are stuctured as (validation_passed, message_delivered, expected_result)
        test_cases = [
            (True, True, self.ack_data_validation_passed_and_message_delivered),
            (True, False, self.ack_data_validation_passed_and_message_not_delivered),
            (False, False, self.ack_data_validation_failed),
            # No need to test validation failed and message delivery passed as this scenario cannot occur
        ]

        for validation_passed, message_delivered, expected_result in test_cases:
            with self.subTest():
                self.assertEqual(
                    make_ack_data(
                        self.message_id,
                        validation_passed,
                        message_delivered,
                        self.created_at_formatted_string,
                    ),
                    expected_result,
                )

    def test_upload_ack_file_success(self):
        """Test that upload_ack_file successfully uploads the ack file"""

        upload_ack_file(
            file_key=FILE_DETAILS.file_key,
            ack_data=deepcopy(self.ack_data_validation_passed_and_message_delivered),
            created_at_formatted_string=FILE_DETAILS.created_at_formatted_string,
        )
        expected_result = [deepcopy(self.ack_data_validation_passed_and_message_delivered)]
        # Note that the data downloaded from the CSV will contain the bool as a string
        expected_result[0]["MESSAGE_DELIVERY"] = "True"
        csv_dict_reader = get_csv_file_dict_reader(
            self.s3_client, BucketNames.DESTINATION, FILE_DETAILS.inf_ack_file_key
        )
        self.assertEqual(list(csv_dict_reader), expected_result)

    def test_upload_ack_file_failure(self):
        """Test that upload_ack_file failed to upload the ack file"""

        upload_ack_file(
            file_key=FILE_DETAILS.file_key,
            ack_data=deepcopy(self.ack_data_validation_passed_and_message_not_delivered),
            created_at_formatted_string=FILE_DETAILS.created_at_formatted_string,
        )
        expected_result = [deepcopy(self.ack_data_validation_passed_and_message_not_delivered)]
        # Note that the data downloaded from the CSV will contain the bool as a string
        expected_result[0]["MESSAGE_DELIVERY"] = "False"
        csv_dict_reader = get_csv_file_dict_reader(
            self.s3_client, BucketNames.DESTINATION, FILE_DETAILS.inf_ack_file_key
        )
        self.assertEqual(list(csv_dict_reader), expected_result)

    def test_make_and_upload_ack_file_success(self):
        """Test that make_and_upload_ack_file uploads an ack file containing the correct values"""
        make_and_upload_ack_file(
            message_id=self.message_id,
            file_key=FILE_DETAILS.file_key,
            validation_passed=True,
            message_delivered=True,
            created_at_formatted_string=FILE_DETAILS.created_at_formatted_string,
        )

        expected_result = [deepcopy(self.ack_data_validation_passed_and_message_delivered)]
        # Note that the data downloaded from the CSV will contain the bool as a string
        expected_result[0]["MESSAGE_DELIVERY"] = "True"
        csv_dict_reader = get_csv_file_dict_reader(
            self.s3_client, BucketNames.DESTINATION, FILE_DETAILS.inf_ack_file_key
        )
        self.assertEqual(list(csv_dict_reader), expected_result)

    def test_make_and_upload_ack_file_failure(self):
        """Test that make_and_upload_ack_file failed to upload an ack file containing the correct values"""
        make_and_upload_ack_file(
            message_id=self.message_id,
            file_key=FILE_DETAILS.file_key,
            validation_passed=True,
            message_delivered=False,
            created_at_formatted_string=FILE_DETAILS.created_at_formatted_string,
        )

        expected_result = [deepcopy(self.ack_data_validation_passed_and_message_not_delivered)]
        # Note that the data downloaded from the CSV will contain the bool as a string
        expected_result[0]["MESSAGE_DELIVERY"] = "False"
        csv_dict_reader = get_csv_file_dict_reader(
            self.s3_client, BucketNames.DESTINATION, FILE_DETAILS.inf_ack_file_key
        )
        self.assertEqual(list(csv_dict_reader), expected_result)


if __name__ == "__main__":
    unittest.main()
