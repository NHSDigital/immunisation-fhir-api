"""Add the filename to the audit table and check for duplicates."""

from clients import dynamodb_client, logger
from errors import UnhandledAuditTableError
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
