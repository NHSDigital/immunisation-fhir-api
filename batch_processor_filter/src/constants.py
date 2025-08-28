import os
from enum import StrEnum

REGION_NAME = "eu-west-2"
AUDIT_TABLE_NAME = os.getenv("AUDIT_TABLE_NAME")
AUDIT_TABLE_FILENAME_GSI = os.getenv("FILE_NAME_GSI")
AUDIT_TABLE_QUEUE_NAME_GSI = os.getenv("QUEUE_NAME_GSI")
QUEUE_URL = os.getenv("QUEUE_URL")
SPLUNK_FIREHOSE_STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME")


class FileStatus(StrEnum):
    """File status constants"""

    QUEUED = "Queued"
    PROCESSING = "Processing"
    PREPROCESSED = "Preprocessed"
    PROCESSED = "Processed"
    DUPLICATE = "Not processed - duplicate"


class AuditTableKeys(StrEnum):
    """Audit table keys"""

    FILENAME = "filename"
    MESSAGE_ID = "message_id"
    QUEUE_NAME = "queue_name"
    STATUS = "status"
    TIMESTAMP = "timestamp"
