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

SUPPLIER_PERMISSIONS_HASH_KEY = "supplier_permissions"
VACCINE_TYPE_TO_DISEASES_HASH_KEY = "vacc_to_diseases"
ODS_CODE_TO_SUPPLIER_SYSTEM_HASH_KEY = "ods_code_to_supplier"

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
    VALID_VERSIONS = ["V5"]
