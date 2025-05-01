"""Add the filename to the audit table and check for duplicates."""

from typing import Union
from boto3.dynamodb.conditions import Key
from clients import dynamodb_client, dynamodb_resource, logger
from errors import UnhandledAuditTableError
from constants import (
    AUDIT_TABLE_NAME,
    AUDIT_TABLE_QUEUE_NAME_GSI,
    FileStatus,
    AuditTableKeys,
)


def get_next_queued_file_details(queue_name: str) -> Union[dict, None]:
    """
    Checks for queued files.
    Returns a dictionary containing the details of the oldest queued file, or returns None if no queued files are found.
    """
    queued_files_found_in_audit_table: dict = dynamodb_resource.Table(
        AUDIT_TABLE_NAME
    ).query(
        IndexName=AUDIT_TABLE_QUEUE_NAME_GSI,
        KeyConditionExpression=Key(AuditTableKeys.QUEUE_NAME).eq(queue_name)
        & Key(AuditTableKeys.STATUS).eq(FileStatus.QUEUED),
    )

    queued_files_details: list = queued_files_found_in_audit_table["Items"]

    # Return the oldest queued file
    return (
        sorted(queued_files_details, key=lambda x: x["timestamp"])[0]
        if queued_files_details
        else None
    )


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
