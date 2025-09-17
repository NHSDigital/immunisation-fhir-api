import boto3
from boto3.dynamodb.conditions import Key

from constants import AUDIT_TABLE_NAME, REGION_NAME, AUDIT_TABLE_FILENAME_GSI, AuditTableKeys, FileStatus, \
    AUDIT_TABLE_QUEUE_NAME_GSI


class BatchAuditRepository:
    """Batch audit repository class."""
    _DUPLICATE_CHECK_FILE_STATUS_CONDITION = (
        Key(AuditTableKeys.STATUS).eq(FileStatus.PROCESSED)
        | Key(AuditTableKeys.STATUS).eq(FileStatus.PREPROCESSED)
        | Key(AuditTableKeys.STATUS).eq(FileStatus.PROCESSING)
    )
    _PROCESSING_AND_FAILED_STATUSES = {FileStatus.PROCESSING, FileStatus.FAILED}

    def __init__(self):
        self._batch_audit_table = boto3.resource("dynamodb", region_name=REGION_NAME).Table(AUDIT_TABLE_NAME)

    def is_duplicate_file(self, file_key: str) -> bool:
        matching_files = self._batch_audit_table.query(
            IndexName=AUDIT_TABLE_FILENAME_GSI,
            KeyConditionExpression=Key(AuditTableKeys.FILENAME).eq(file_key),
            FilterExpression=self._DUPLICATE_CHECK_FILE_STATUS_CONDITION
        ).get("Items", [])

        return len(matching_files) > 0

    def is_event_processing_or_failed_for_supplier_and_vacc_type(self, supplier: str, vacc_type: str) -> bool:
        queue_name = f"{supplier}_{vacc_type}"

        for status in self._PROCESSING_AND_FAILED_STATUSES:
            files_in_queue = self._batch_audit_table.query(
                IndexName=AUDIT_TABLE_QUEUE_NAME_GSI,
                KeyConditionExpression=Key(AuditTableKeys.QUEUE_NAME).eq(queue_name) & Key(AuditTableKeys.STATUS)
                .eq(status)
            ).get("Items", [])

            if len(files_in_queue) > 0:
                return True

        return False

    def update_status(self, message_id: str, updated_status: str) -> None:
        self._batch_audit_table.update_item(
            Key={AuditTableKeys.MESSAGE_ID: message_id},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": updated_status},
            ConditionExpression="attribute_exists(message_id)"
        )
