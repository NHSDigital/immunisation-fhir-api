"""File of values which can be used for testing"""

from datetime import datetime
from unittest.mock import patch

from utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.models.batch_constants import AuditTableKeys


fixed_datetime = datetime(2024, 10, 29, 12, 0, 0)

# Mock_created_at_formatted string is used throughout the test suite, so that the ack file name
# (which includes the created_at_formatted_string) can be predicted.
# NOTE That that file details for files numbered anything other than one will have a different
# created_at_formatted_string (the final digit of the year will be the file number, rather than '1')
MOCK_CREATED_AT_FORMATTED_STRING = "20010101T00000000"
MOCK_EXPIRES_AT = 947808000


class FileDetails:
    """
    Class to create and hold values for a mock file, based on the vaccine type, supplier and ods code.
    NOTE: Supplier and ODS code are hardcoded rather than mapped, for testing purposes.
    NOTE: The permissions_list and permissions_config are examples of full permissions for the suppler for the
    vaccine type.
    """

    def __init__(
        self,
        supplier: str = "RAVS",
        vaccine_type: str = None,
        ods_code: str = None,
        file_number: int = 1,
        organization_code: str = None,
    ):
        self.vaccine_type = vaccine_type.upper() if vaccine_type else None
        self.ods_code = ods_code.upper() if ods_code else "X8E5B"
        self.supplier = supplier.upper() if supplier else None
        self.queue_name = f"{self.supplier}_{self.vaccine_type}"

        self.created_at_formatted_string = f"200{file_number}0101T00000000"
        self.expires_at = MOCK_EXPIRES_AT
        self.message_id = f"{self.supplier}_{self.vaccine_type}_test_id_{file_number}"
        self.name = f"{self.vaccine_type}/ {self.supplier} file"

        file_date_and_time_string = f"20000101T0000000{file_number}"
        extended_attributes_prefix = "Vaccination_Extended_Attributes"
        if vaccine_type.startswith(extended_attributes_prefix):
            file_key = f"{extended_attributes_prefix}_v1_5_{organization_code}_{file_date_and_time_string}.csv"
        else:
            file_key = f"{vaccine_type}_Vaccinations_v5_{ods_code}_{file_date_and_time_string}.csv"

        self.file_key = file_key

        self.ack_file_key = f"ack/{self.file_key[:-4]}_InfAck_{self.created_at_formatted_string}.csv"

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
            AuditTableKeys.EXPIRES_AT: {"N": str(self.expires_at)},
        }


class MockFileDetails:
    """Class containing mock file details for use in tests"""

    ravs_rsv_1 = FileDetails("RAVS", "RSV", "X8E5B", file_number=1)
    ravs_rsv_2 = FileDetails("RAVS", "RSV", "X8E5B", file_number=2)
    ravs_rsv_3 = FileDetails("RAVS", "RSV", "X8E5B", file_number=3)
    ravs_rsv_4 = FileDetails("RAVS", "RSV", "X8E5B", file_number=4)
    ravs_rsv_5 = FileDetails("RAVS", "RSV", "X8E5B", file_number=5)
    emis_flu = FileDetails("EMIS", "FLU", "YGM41")
    emis_rsv = FileDetails("EMIS", "RSV", "YGM41")
    ravs_flu = FileDetails("RAVS", "FLU", "X8E5B")
    extended_attributes_file = FileDetails(
        vaccine_type="Vaccination_Extended_Attributes", file_number=1, organization_code="X8E5B"
    )


MOCK_FILE_HEADERS = (
    "NHS_NUMBER|PERSON_FORENAME|PERSON_SURNAME|PERSON_DOB|PERSON_GENDER_CODE|PERSON_POSTCODE|"
    "DATE_AND_TIME|SITE_CODE|SITE_CODE_TYPE_URI|UNIQUE_ID|UNIQUE_ID_URI|ACTION_FLAG|"
    "PERFORMING_PROFESSIONAL_FORENAME|PERFORMING_PROFESSIONAL_SURNAME|RECORDED_DATE|"
    "PRIMARY_SOURCE|VACCINATION_PROCEDURE_CODE|VACCINATION_PROCEDURE_TERM|DOSE_SEQUENCE|"
    "VACCINE_PRODUCT_CODE|VACCINE_PRODUCT_TERM|VACCINE_MANUFACTURER|BATCH_NUMBER|EXPIRY_DATE|"
    "SITE_OF_VACCINATION_CODE|SITE_OF_VACCINATION_TERM|ROUTE_OF_VACCINATION_CODE|"
    "ROUTE_OF_VACCINATION_TERM|DOSE_AMOUNT|DOSE_UNIT_CODE|DOSE_UNIT_TERM|INDICATION_CODE|"
    "LOCATION_CODE|LOCATION_CODE_TYPE_URI"
) + "\n"

# The content does not matter for the filename processor Lambda. It only needs to ensure the file is not empty.
# Validation of the headers and contents happens later in the batch flow
MOCK_FILE_DATA = (
    '9674963871|"ALAN"|"PARTRIDGE"|"20190131"|"2"|"AA14 6AA"|"20240610T183325"|"J82067"|'
    '"https://fhir.nhs.uk/Id/ods-organization-code"|"1234"|"a_system"|"new"|"Ellena"|"O\'Reilly"|"20240101"|"TRUE"|'
    '"1303503001"|"Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"|'
    '1|"42605811000001109"|"Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) '
    '(product)"|"Pfizer"|"RSVTEST"|"20241231"|"368208006"|"Left upper arm structure (body structure)"|'
    '"78421000"|"Intramuscular route (qualifier value)"|"0.5"|"258773002"|"Milliliter (qualifier value)"|"Test"|'
    '"J82067"|"https://fhir.nhs.uk/Id/ods-organization-code"'
)

MOCK_EXTENDED_ATTRIBUTES_FILE_DATA = '"VACCINATION_UNIQUE_ID"|"VACCINATION_UNIQUE_ID_URI"|"ACTION_FLAG"|"ATTRIBUTE_ID"|"ATTRIBUTE_DISPLAYED_TEXT"|"ATTRIBUTE_VALUE"|"RECORDED_DATE"'

MOCK_EXTENDED_ATTRIBUTES_FILE_DATA = '"e045626e-4dc5-4df3-bc35-da25263f901e"|"https://supplierABC/identifiers/vacc"|"new"|"003"|"Are you a health care worker?"|"NOT_SPECIFIED"|"20210801"'

MOCK_BATCH_FILE_CONTENT = MOCK_FILE_HEADERS + MOCK_FILE_DATA
MOCK_EXTENDED_ATTRIBUTES_FILE_CONTENT = MOCK_FILE_HEADERS + MOCK_EXTENDED_ATTRIBUTES_FILE_DATA
