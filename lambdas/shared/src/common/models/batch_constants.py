from enum import StrEnum


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
    EMPTY = "Empty file"
    UNAUTHORISED = "Unauthorised"


class AuditTableKeys(StrEnum):  #
    """Audit table keys"""

    FILENAME = "filename"
    MESSAGE_ID = "message_id"
    QUEUE_NAME = "queue_name"
    RECORD_COUNT = "record_count"
    STATUS = "status"
    TIMESTAMP = "timestamp"
    EXPIRES_AT = "expires_at"
    INGESTION_START_TIME = "ingestion_start_time"
    INGESTION_END_TIME = "ingestion_end_time"
    RECORDS_SUCCEEDED = "records_succeeded"
    RECORDS_FAILED = "records_failed"
    ERROR_DETAILS = "error_details"


class Operation(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class Permission(StrEnum):
    CREATE = "C"
    UPDATE = "U"
    DELETE = "D"


permission_to_operation_map = {
    Permission.CREATE: Operation.CREATE,
    Permission.UPDATE: Operation.UPDATE,
    Permission.DELETE: Operation.DELETE,
}
