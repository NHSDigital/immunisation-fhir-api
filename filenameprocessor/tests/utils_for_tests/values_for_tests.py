"""File of values which can be used for testing"""

from unittest.mock import patch
from datetime import datetime

from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from constants import AuditTableKeys


fixed_datetime = datetime(2024, 10, 29, 12, 0, 0)

# Mock_created_at_formatted string is used throughout the test suite, so that the ack file name
# (which includes the created_at_formatted_string) can be predicted.
# NOTE That that file details for files numbered anything other than one will have a different
# created_at_formatted_string (the final digit of the year will be the file number, rather than '1')
MOCK_CREATED_AT_FORMATTED_STRING = "20010101T00000000"


class FileDetails:
    """
    Class to create and hold values for a mock file, based on the vaccine type, supplier and ods code.
    NOTE: Supplier and ODS code are hardcoded rather than mapped, for testing purposes.
    NOTE: The permissions_list and permissions_config are examples of full permissions for the suppler for the
    vaccine type.
    """

    def __init__(
        self, supplier: str, vaccine_type: str, ods_code: str, file_number: int = 1
    ):
        self.vaccine_type = vaccine_type.upper()
        self.ods_code = ods_code.upper()
        self.supplier = supplier.upper()
        self.queue_name = f"{self.supplier}_{self.vaccine_type}"

        self.created_at_formatted_string = f"200{file_number}0101T00000000"
        self.message_id = f"{self.supplier}_{self.vaccine_type}_test_id_{file_number}"
        self.name = f"{self.vaccine_type}/ {self.supplier} file"

        file_date_and_time_string = f"20000101T0000000{file_number}"
        self.file_key = (
            f"{vaccine_type}_Vaccinations_v5_{ods_code}_{file_date_and_time_string}.csv"
        )
        self.ack_file_key = (
            f"ack/{self.file_key[:-4]}_InfAck_{self.created_at_formatted_string}.csv"
        )

        self.permissions_list = [f"{self.vaccine_type}_FULL"]
        self.permissions_config = {self.supplier: self.permissions_list}

        # DO NOT CHANGE THE SQS MESSAGE BODY UNLESS THE IMPLEMENTATION OF THE MESSAGE BODY IS CHANGED - IT IS USED
        # FOR TEST ASSERTIONS TO ENSURE TEH SQS MESSAGE BODY IS AS EXPECTED
        self.sqs_message_body = {
            "message_id": self.message_id,
            "vaccine_type": self.vaccine_type,
            "supplier": self.supplier,
            "filename": self.file_key,
            "permission": self.permissions_list,
            "created_at_formatted_string": self.created_at_formatted_string,
        }

        # NOTE THAT AUDIT_TABLE_ENTRY IS MISSING THE FILE STATUS - THIS MUST BE SPECIFIED AT THE TIME THE ENTRY
        # IS USED IN A TEST
        self.audit_table_entry = {
            AuditTableKeys.MESSAGE_ID: {"S": self.message_id},
            AuditTableKeys.FILENAME: {"S": self.file_key},
            AuditTableKeys.QUEUE_NAME: {"S": self.queue_name},
            AuditTableKeys.TIMESTAMP: {"S": self.created_at_formatted_string},
        }


class MockFileDetails:
    """Class containing mock file details for use in tests"""

    ravs_rsv_1 = FileDetails("RAVS", "RSV", "X26", file_number=1)
    ravs_rsv_2 = FileDetails("RAVS", "RSV", "X26", file_number=2)
    ravs_rsv_3 = FileDetails("RAVS", "RSV", "X26", file_number=3)
    ravs_rsv_4 = FileDetails("RAVS", "RSV", "X26", file_number=4)
    ravs_rsv_5 = FileDetails("RAVS", "RSV", "X26", file_number=5)
    emis_flu = FileDetails("EMIS", "FLU", "YGM41")
    emis_rsv = FileDetails("EMIS", "RSV", "YGM41")
    ravs_flu = FileDetails("RAVS", "FLU", "X26")
