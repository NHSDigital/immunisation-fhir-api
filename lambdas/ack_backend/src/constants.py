"""Constants for ack lambda"""

import os

AUDIT_TABLE_NAME = os.getenv("AUDIT_TABLE_NAME")

COMPLETED_ACK_DIR = "forwardedFile"
TEMP_ACK_DIR = "TempAck"
BATCH_FILE_PROCESSING_DIR = "processing"
BATCH_FILE_ARCHIVE_DIR = "archive"


def get_source_bucket_name() -> str:
    """Get the SOURCE_BUCKET_NAME environment from environment variables."""
    return os.getenv("SOURCE_BUCKET_NAME")


def get_ack_bucket_name() -> str:
    """Get the ACK_BUCKET_NAME environment from environment variables."""
    return os.getenv("ACK_BUCKET_NAME")


class FileStatus:
    """File status constants"""

    QUEUED = "Queued"
    PROCESSING = "Processing"
    PROCESSED = "Processed"
    DUPLICATE = "Duplicate"


class AuditTableKeys:
    """Audit table keys"""

    FILENAME = "filename"
    MESSAGE_ID = "message_id"
    QUEUE_NAME = "queue_name"
    RECORD_COUNT = "record_count"
    STATUS = "status"
    TIMESTAMP = "timestamp"
    INGESTION_COMPLETE = "ingestion_complete"
    RECORDS_SUCCEEDED = "records_succeeded"
    RECORDS_FAILED = "records_failed"


ACK_HEADERS = [
    "MESSAGE_HEADER_ID",
    "HEADER_RESPONSE_CODE",
    "ISSUE_SEVERITY",
    "ISSUE_CODE",
    "ISSUE_DETAILS_CODE",
    "RESPONSE_TYPE",
    "RESPONSE_CODE",
    "RESPONSE_DISPLAY",
    "RECEIVED_TIME",
    "MAILBOX_FROM",
    "LOCAL_ID",
    "IMMS_ID",
    "OPERATION_OUTCOME",
    "MESSAGE_DELIVERY",
]
