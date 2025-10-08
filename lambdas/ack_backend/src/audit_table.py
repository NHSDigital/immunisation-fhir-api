"""Add the filename to the audit table and check for duplicates."""
from typing import Optional
from common.clients import dynamodb_client, logger
from common.models.errors import UnhandledAuditTableError
from constants import AUDIT_TABLE_NAME, FileStatus, AuditTableKeys


def change_audit_table_status_to_processed(file_key: str, message_id: str) -> None:
    """Updates the status in the audit table to 'Processed' and returns the queue name."""
    try:
        # Update the status in the audit table to "Processed"
        dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": {"S": FileStatus.PROCESSED}},
            ConditionExpression="attribute_exists(message_id)",
        )

        logger.info(
            "The status of %s file, with message id %s, was successfully updated to %s in the audit table",
            file_key,
            message_id,
            FileStatus.PROCESSED,
        )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error


def get_record_count_by_message_id(event_message_id: str) -> Optional[int]:
    """Retrieves full audit entry by unique event message ID"""
    audit_record = dynamodb_client.get_item(
        TableName=AUDIT_TABLE_NAME,
        Key={AuditTableKeys.MESSAGE_ID: {"S": event_message_id}}
    )

    record_count = audit_record.get("Item", {}).get(AuditTableKeys.RECORD_COUNT, {}).get("N")

    if not record_count:
        return None

    return int(record_count)
