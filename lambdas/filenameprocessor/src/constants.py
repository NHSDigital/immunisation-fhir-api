"""Constants for the filenameprocessor lambda"""

import os

from common.models.errors import UnhandledAuditTableError
from models.errors import (
    InvalidFileKeyError,
    UnhandledSqsError,
    VaccineTypePermissionsError,
)

SOURCE_BUCKET_NAME = os.getenv("SOURCE_BUCKET_NAME")


DPS_DESTINATION_BUCKET_NAME = os.getenv("DPS_BUCKET_NAME")
EXPECTED_SOURCE_BUCKET_ACCOUNT = os.getenv("ACCOUNT_ID")
EXPECTED_DPS_DESTINATION_ACCOUNT = os.getenv("DPS_ACCOUNT_ID")
AUDIT_TABLE_NAME = os.getenv("AUDIT_TABLE_NAME")
AUDIT_TABLE_TTL_DAYS = os.getenv("AUDIT_TABLE_TTL_DAYS")
VALID_VERSIONS = ["V5"]

ODS_CODE_TO_SUPPLIER_SYSTEM_HASH_KEY = "ods_code_to_supplier"
EXTENDED_ATTRIBUTES_FILE_PREFIX = "Vaccination_Extended_Attributes"

# Currently only COVID extended attributes files are supported, might be extended in future for other vaccine types
EXTENDED_ATTRIBUTES_VACC_TYPE = "COVID"

DPS_DESTINATION_PREFIX = "dps_destination"
EXTENDED_ATTRIBUTES_ARCHIVE_PREFIX = "extended-attributes-archive"
VALID_EA_VERSIONS = ["V1_5"]
ERROR_TYPE_TO_STATUS_CODE_MAP = {
    VaccineTypePermissionsError: 403,
    InvalidFileKeyError: 400,  # Includes invalid ODS code, therefore unable to identify supplier
    UnhandledAuditTableError: 500,
    UnhandledSqsError: 500,
    Exception: 500,
}

# Filename timestamp constants
VALID_TIMESTAMP_LENGTH = 17
VALID_TIMEZONE_OFFSETS = {"00", "01"}


class Operation(str):  # TODO: shared but needs work
    CREATE = "C"
    UPDATE = "U"
    DELETE = "D"
