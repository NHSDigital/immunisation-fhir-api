import os
from enum import StrEnum

AUDIT_TABLE_NAME = os.getenv("AUDIT_TABLE_NAME")
AUDIT_TABLE_FILENAME_GSI = os.getenv("FILE_NAME_GSI")
AUDIT_TABLE_QUEUE_NAME_GSI = os.getenv("QUEUE_NAME_GSI")
QUEUE_URL = os.getenv("QUEUE_URL")
SPLUNK_FIREHOSE_STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME")
SOURCE_BUCKET_NAME = os.getenv("SOURCE_BUCKET_NAME")
ACK_BUCKET_NAME = os.getenv("ACK_BUCKET_NAME")


class FileStatus(StrEnum):
    """File status constants"""

    QUEUED = "Queued"
    PROCESSING = "Processing"
    PREPROCESSED = "Preprocessed"
    PROCESSED = "Processed"
    NOT_PROCESSED = "Not processed"
    FAILED = "Failed"


class FileNotProcessedReason(StrEnum):
    """Reasons why a file was not processed"""

    DUPLICATE = "Duplicate"


class AuditTableKeys(StrEnum):
    """Audit table keys"""

    MESSAGE_ID = "message_id"
    FILENAME = "filename"
    QUEUE_NAME = "queue_name"
    STATUS = "status"
    ERROR_DETAILS = "error_details"
    TIMESTAMP = "timestamp"
    COMPLETED_AT = "completed_at"
    RECORD_COUNT = "record_count"
    RECORDS_SUCCEEDED = "records_succeeded"
    RECORDS_FAILED = "records_failed"
    EXPIRES_AT = "expires_at"
