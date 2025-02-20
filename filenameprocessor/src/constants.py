"""Constants for the filenameprocessor lambda"""

import os
from errors import (
    VaccineTypePermissionsError,
    InvalidFileKeyError,
    InvalidSupplierError,
    UnhandledAuditTableError,
    DuplicateFileError,
    UnhandledSqsError,
)

SOURCE_BUCKET_NAME = os.getenv("SOURCE_BUCKET_NAME")
FILE_NAME_PROC_LAMBDA_NAME = os.getenv("FILE_NAME_PROC_LAMBDA_NAME")
AUDIT_TABLE_NAME = os.getenv("AUDIT_TABLE_NAME")
AUDIT_TABLE_QUEUE_NAME_GSI = "queue_name_index"
AUDIT_TABLE_FILENAME_GSI = "filename_index"

PERMISSIONS_CONFIG_FILE_KEY = "permissions_config.json"

ERROR_TYPE_TO_STATUS_CODE_MAP = {
    VaccineTypePermissionsError: 403,
    InvalidFileKeyError: 400,  # Includes invalid ODS code, therefore unable to identify supplier
    InvalidSupplierError: 500,  # Only raised if supplier variable is not correctly set
    UnhandledAuditTableError: 500,
    DuplicateFileError: 422,
    UnhandledSqsError: 500,
    Exception: 500,
}


class FileStatus:
    """File status constants"""

    QUEUED = "Queued"
    PROCESSING = "Processing"
    PROCESSED = "Processed"
    DUPLICATE = "Not processed - duplicate"


class AuditTableKeys:
    """Audit table keys"""

    FILENAME = "filename"
    MESSAGE_ID = "message_id"
    QUEUE_NAME = "queue_name"
    STATUS = "status"
    TIMESTAMP = "timestamp"


class Constants:
    """Constants for the filenameprocessor lambda"""

    VALID_VACCINE_TYPES = ["FLU", "COVID19", "MMR", "RSV"]

    VALID_VERSIONS = ["V5"]

    # Mappings from ODS code to supplier name.
    # NOTE: Any ODS code not found in this dictionary's keys is invalid for this service
    ODS_TO_SUPPLIER_MAPPINGS = {
        "YGM41": "EMIS",
        "8J1100001": "PINNACLE",
        "8HK48": "SONAR",
        "YGA": "TPP",
        "0DE": "AGEM-NIVS",
        "0DF": "NIMS",
        "8HA94": "EVA",
        "X26": "RAVS",
        "YGMYH": "MEDICAL_DIRECTOR",
        "W00": "WELSH_DA_1",
        "W000": "WELSH_DA_2",
        "ZT001": "NORTHERN_IRELAND_DA",
        "YA7": "SCOTLAND_DA",
        "N2N9I": "COVID19_VACCINE_RESOLUTION_SERVICEDESK",
        "YGJ": "EMIS",
        "DPSREDUCED": "DPSREDUCED",
        "DPSFULL": "DPSFULL",
    }
