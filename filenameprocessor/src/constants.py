"""Constants for the filenameprocessor lambda"""

import os
from enum import StrEnum

from errors import (
    VaccineTypePermissionsError,
    InvalidFileKeyError,
    InvalidSupplierError,
    UnhandledAuditTableError,
    DuplicateFileError,
    UnhandledSqsError, EmptyFileError,
)

SOURCE_BUCKET_NAME = os.getenv("SOURCE_BUCKET_NAME")
AUDIT_TABLE_NAME = os.getenv("AUDIT_TABLE_NAME")
AUDIT_TABLE_TTL_DAYS = os.getenv("AUDIT_TABLE_TTL_DAYS")

EXPECTED_NUMBER_OF_FILE_KEY_PARTS = 5
VALID_VERSIONS = {"V5"}
VALID_FILE_EXTENSIONS = {"CSV", "DAT"}

SUPPLIER_PERMISSIONS_HASH_KEY = "supplier_permissions"
VACCINE_TYPE_TO_DISEASES_HASH_KEY = "vacc_to_diseases"
ODS_CODE_TO_SUPPLIER_SYSTEM_HASH_KEY = "ods_code_to_supplier"

ERROR_TYPE_TO_STATUS_CODE_MAP = {
    VaccineTypePermissionsError: 403,
    InvalidFileKeyError: 400,  # Includes invalid ODS code, therefore unable to identify supplier
    EmptyFileError: 400,
    InvalidSupplierError: 500,  # Only raised if supplier variable is not correctly set
    UnhandledAuditTableError: 500,
    DuplicateFileError: 422,
    UnhandledSqsError: 500,
    Exception: 500,
}

# The size in bytes of an empty batch file containing only the headers row
EMPTY_BATCH_FILE_SIZE_IN_BYTES = 615


class FileStatus(StrEnum):
    """File status constants"""

    QUEUED = "Queued"
    PROCESSING = "Processing"
    PROCESSED = "Processed"
    DUPLICATE = "Not processed - duplicate"
    EMPTY = "Not processed - empty file"


class AuditTableKeys(StrEnum):
    """Audit table keys"""

    FILENAME = "filename"
    MESSAGE_ID = "message_id"
    QUEUE_NAME = "queue_name"
    STATUS = "status"
    TIMESTAMP = "timestamp"
    EXPIRES_AT = "expires_at"
