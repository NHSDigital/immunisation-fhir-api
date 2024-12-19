"""Tests for update_ack_file.py"""

import unittest
from make_and_upload_ack_file import make_ack_data


class TestUpdateAckFile(unittest.TestCase):
    "Tests for update_ack_file.py"

    def setUp(self) -> None:
        self.message_id = "test_id"
        self.created_at_formatted_string = "20200101T12345600"
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
                        self.message_id, validation_passed, message_delivered, self.created_at_formatted_string
                    ),
                    expected_result,
                )


if __name__ == "__main__":
    unittest.main()
