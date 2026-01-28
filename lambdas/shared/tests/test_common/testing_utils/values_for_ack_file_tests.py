"""Values for use in tests"""

import json
from unittest.mock import patch

from test_common.testing_utils.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
)

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.models.batch_constants import AuditTableKeys


class FileDetails:
    """
    Class to create and hold values for a mock file, based on the vaccine type, supplier and ods code.
    NOTE: Supplier and ODS code are hardcoded rather than mapped, for testing purposes.
    NOTE: The permissions_list and permissions_config are examples of full permissions for the suppler for the
    vaccine type.
    """

    def __init__(self, vaccine_type: str, supplier: str, ods_code: str, file_number: int = 1):
        self.name = f"{vaccine_type.upper()}/ {supplier.upper()} file"
        self.created_at_formatted_string = f"202{file_number}1120T12000000"
        self.file_key = f"{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv"
        self.inf_ack_file_key = (
            f"ack/{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000"
            + f"_InfAck_{self.created_at_formatted_string}.csv"
        )
        self.ack_file_key = f"processedFile/{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000_response.csv"
        self.vaccine_type = vaccine_type
        self.ods_code = ods_code
        self.supplier = supplier
        self.file_date_and_time_string = f"20000101T0000000{file_number}"
        self.message_id = f"{vaccine_type.lower()}_{supplier.lower()}_test_id"
        self.message_id_order = f"{vaccine_type.lower()}_{supplier.lower()}_test_id_{file_number}"
        self.full_permissions_list = [f"{vaccine_type}.CRUD"]
        self.create_permissions_only = [f"{vaccine_type}.C"]
        self.update_permissions_only = [f"{vaccine_type}.U"]
        self.delete_permissions_only = [f"{vaccine_type}.D"]

        self.queue_name = f"{supplier}_{vaccine_type}"

        self.base_event = {
            "message_id": self.message_id,
            "vaccine_type": vaccine_type,
            "supplier": supplier,
            "filename": self.file_key,
            "created_at_formatted_string": self.created_at_formatted_string,
        }

        # Mock the event details which would be receeived from SQS message
        self.event_full_permissions_dict = {
            **self.base_event,
            "permission": self.full_permissions_list,
        }
        self.event_create_permissions_only_dict = {
            **self.base_event,
            "permission": self.create_permissions_only,
        }
        self.event_update_permissions_only_dict = {
            **self.base_event,
            "permission": self.update_permissions_only,
        }
        self.event_delete_permissions_only_dict = {
            **self.base_event,
            "permission": self.delete_permissions_only,
        }
        self.event_no_permissions_dict = {**self.base_event, "permission": []}
        self.event_full_permissions = json.dumps(self.event_full_permissions_dict)
        self.event_create_permissions_only = json.dumps(self.event_create_permissions_only_dict)
        self.event_update_permissions_only = json.dumps(self.event_update_permissions_only_dict)
        self.event_delete_permissions_only = json.dumps(self.event_delete_permissions_only_dict)
        self.event_no_permissions = json.dumps(self.event_no_permissions_dict)

        self.audit_table_entry = {
            AuditTableKeys.MESSAGE_ID: {"S": self.message_id},
            AuditTableKeys.FILENAME: {"S": self.file_key},
            AuditTableKeys.QUEUE_NAME: {"S": self.queue_name},
            AuditTableKeys.TIMESTAMP: {"S": self.created_at_formatted_string},
        }


class MockFileDetails:
    """Class containing mock file details for use in tests"""

    ravs_rsv_1 = FileDetails("RSV", "RAVS", "X26", file_number=1)
    ravs_rsv_2 = FileDetails("RSV", "RAVS", "X26", file_number=2)
    ravs_rsv_3 = FileDetails("RSV", "RAVS", "X26", file_number=3)
    ravs_rsv_4 = FileDetails("RSV", "RAVS", "X26", file_number=4)
    ravs_rsv_5 = FileDetails("RSV", "RAVS", "X26", file_number=5)
    rsv_ravs = FileDetails("RSV", "RAVS", "X26")
    rsv_emis = FileDetails("RSV", "EMIS", "8HK48")
    flu_emis = FileDetails("FLU", "EMIS", "YGM41")
    ravs_flu = FileDetails("FLU", "RSV", "X26")
