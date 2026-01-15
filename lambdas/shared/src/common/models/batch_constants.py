import os
from enum import StrEnum

ACK_BUCKET_NAME = os.getenv("ACK_BUCKET_NAME")
AUDIT_TABLE_NAME = os.getenv("AUDIT_TABLE_NAME")
SOURCE_BUCKET_NAME = os.getenv("SOURCE_BUCKET_NAME")


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


class AuditTableKeys(StrEnum):
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


# It would be better to use boto3.dynamodb.types for these constants but it could cause issues across shared lambdas
# with different dependencies
class AuditTableKeyDataTypes:
    STRING = "S"
    NUMBER = "N"


audit_table_key_data_types_map = {
    AuditTableKeys.FILENAME: AuditTableKeyDataTypes.STRING,
    AuditTableKeys.MESSAGE_ID: AuditTableKeyDataTypes.STRING,
    AuditTableKeys.QUEUE_NAME: AuditTableKeyDataTypes.STRING,
    AuditTableKeys.RECORD_COUNT: AuditTableKeyDataTypes.NUMBER,
    AuditTableKeys.STATUS: AuditTableKeyDataTypes.STRING,
    AuditTableKeys.TIMESTAMP: AuditTableKeyDataTypes.STRING,
    AuditTableKeys.EXPIRES_AT: AuditTableKeyDataTypes.NUMBER,
    AuditTableKeys.INGESTION_START_TIME: AuditTableKeyDataTypes.STRING,
    AuditTableKeys.INGESTION_END_TIME: AuditTableKeyDataTypes.STRING,
    AuditTableKeys.RECORDS_SUCCEEDED: AuditTableKeyDataTypes.NUMBER,
    AuditTableKeys.RECORDS_FAILED: AuditTableKeyDataTypes.NUMBER,
    AuditTableKeys.ERROR_DETAILS: AuditTableKeyDataTypes.STRING,
}


class Operation(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class OperationShortCode(StrEnum):
    CREATE = "C"
    UPDATE = "U"
    DELETE = "D"


permission_to_operation_map = {
    OperationShortCode.CREATE: Operation.CREATE,
    OperationShortCode.UPDATE: Operation.UPDATE,
    OperationShortCode.DELETE: Operation.DELETE,
}
