"""Add the filename to the audit table and check for duplicates."""
from clients import dynamodb_client, logger
from errors import UnhandledAuditTableError
from constants import AUDIT_TABLE_NAME, AuditTableKeys


def upsert_audit_table(
    message_id: str,
    file_key: str,
    created_at_formatted_str: str,
    expiry_timestamp: int,
    queue_name: str,
    file_status: str
) -> None:
    """
    Updates the audit table with the file details
    """
    try:
        # Add to the audit table (regardless of whether it is a duplicate)
        dynamodb_client.put_item(
            TableName=AUDIT_TABLE_NAME,
            Item={
                AuditTableKeys.MESSAGE_ID: {"S": message_id},
                AuditTableKeys.FILENAME: {"S": file_key},
                AuditTableKeys.QUEUE_NAME: {"S": queue_name},
                AuditTableKeys.STATUS: {"S": file_status},
                AuditTableKeys.TIMESTAMP: {"S": created_at_formatted_str},
                AuditTableKeys.EXPIRES_AT: {"N": str(expiry_timestamp)},
            },
            ConditionExpression="attribute_not_exists(message_id)",  # Prevents accidental overwrites
        )
        logger.info("%s file, with message id %s, successfully added to audit table", file_key, message_id)

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error
