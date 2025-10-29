"""Constants for the filenameprocessor lambda"""

import os
from enum import StrEnum

from common.models.errors import (
    InvalidFileKeyError,
    UnhandledAuditTableError,
    UnhandledSqsError,
    VaccineTypePermissionsError,
)

SOURCE_BUCKET_NAME = os.getenv("SOURCE_BUCKET_NAME")
AUDIT_TABLE_NAME = os.getenv("AUDIT_TABLE_NAME")
AUDIT_TABLE_TTL_DAYS = os.getenv("AUDIT_TABLE_TTL_DAYS")
VALID_VERSIONS = ["V5"]

SUPPLIER_PERMISSIONS_HASH_KEY = "supplier_permissions"
VACCINE_TYPE_TO_DISEASES_HASH_KEY = "vacc_to_diseases"
ODS_CODE_TO_SUPPLIER_SYSTEM_HASH_KEY = "ods_code_to_supplier"

ERROR_TYPE_TO_STATUS_CODE_MAP = {
    VaccineTypePermissionsError: 403,
    InvalidFileKeyError: 400,  # Includes invalid ODS code, therefore unable to identify supplier
    UnhandledAuditTableError: 500,
    UnhandledSqsError: 500,
    Exception: 500,
}


class FileStatus(StrEnum):
    """File status constants"""

    QUEUED = "Queued"
    PROCESSING = "Processing"
    PROCESSED = "Processed"
    NOT_PROCESSED = "Not processed"
    FAILED = "Failed"


class FileNotProcessedReason(StrEnum):
    """Reasons why a file was not processed"""

    EMPTY = "Empty file"
    UNAUTHORISED = "Unauthorised"


class AuditTableKeys(StrEnum):
    """Audit table keys"""

    FILENAME = "filename"
    MESSAGE_ID = "message_id"
    QUEUE_NAME = "queue_name"
    STATUS = "status"
    TIMESTAMP = "timestamp"
    EXPIRES_AT = "expires_at"
    ERROR_DETAILS = "error_details"
