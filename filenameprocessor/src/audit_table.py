"""Add the filename to the audit table and check for duplicates."""

from typing import Union
from boto3.dynamodb.conditions import Key
from clients import dynamodb_client, dynamodb_resource, logger
from errors import DuplicateFileError, UnhandledAuditTableError
from constants import AUDIT_TABLE_NAME, AUDIT_TABLE_QUEUE_NAME_GSI, AUDIT_TABLE_FILENAME_GSI, AuditTableKeys, FileStatus


def get_next_queued_file_details(queue_name: str) -> Union[dict, None]:
    """
    Checks for queued files.
    Returns a dictionary containing the details of the oldest queued file, or returns None if no queued files are found.
    """
    queued_files_found_in_audit_table: dict = dynamodb_resource.Table(AUDIT_TABLE_NAME).query(
        IndexName=AUDIT_TABLE_QUEUE_NAME_GSI,
        KeyConditionExpression=Key(AuditTableKeys.QUEUE_NAME).eq(queue_name)
        & Key(AuditTableKeys.STATUS).eq(FileStatus.QUEUED),
    )

    queued_files_details: list = queued_files_found_in_audit_table["Items"]

    # Return the oldest queued file
    return sorted(queued_files_details, key=lambda x: x["timestamp"])[0] if queued_files_details else None


def ensure_file_is_not_a_duplicate(file_key: str, created_at_formatted_string: str) -> None:
    """Raises an error if the file is a duplicate."""
    files_already_in_audit_table = (
        dynamodb_resource.Table(AUDIT_TABLE_NAME)
        .query(IndexName=AUDIT_TABLE_FILENAME_GSI, KeyConditionExpression=Key(AuditTableKeys.FILENAME).eq(file_key))
        .get("Items")
    )
    if files_already_in_audit_table:
        logger.error("%s file duplicate added to s3 at the following time: %s", file_key, created_at_formatted_string)
        raise DuplicateFileError(f"Duplicate file: {file_key} added at {created_at_formatted_string}")


def upsert_audit_table(
    message_id: str,
    file_key: str,
    created_at_formatted_str: str,
    queue_name: str,
    file_status: str,
    is_existing_file: bool,
) -> bool:
    """
    Updates the audit table with the file details. Returns a bool indicating whether the file status is queued
    (i.e. if the file has passed initial validation and there are no other files in the queue, then the file is status
    will be 'processing' and the file is ready to be sent for row level processing.)
    """
    try:
        # If the file is not new, then the lambda has been invoked by the next file in the queue for processing
        if is_existing_file:
            dynamodb_client.update_item(
                TableName=AUDIT_TABLE_NAME,
                Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
                UpdateExpression="SET #status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": {"S": file_status}},
                ConditionExpression="attribute_exists(message_id)",
            )
            logger.info("%s file set for processing, and the status successfully updated in audit table", file_key)
            return False

        # If the file is not already processed, check whether there is a file ahead in the queue already processing
        if file_status not in (FileStatus.PROCESSED, FileStatus.DUPLICATE):
            files_in_processing = dynamodb_resource.Table(AUDIT_TABLE_NAME).query(
                IndexName=AUDIT_TABLE_QUEUE_NAME_GSI,
                KeyConditionExpression=Key(AuditTableKeys.QUEUE_NAME).eq(queue_name)
                & Key(AuditTableKeys.STATUS).eq(FileStatus.PROCESSING),
            )
            # TODO: There is a short time lag between a file being marked as processed, and the next queued file being
            # marked as processing. If a third file is added to the queue during this time this could result in
            # two files processing simultanously. This is a known issue which needs to be addressed in a future
            # iteration.
            if files_in_processing["Items"]:
                file_status = FileStatus.QUEUED
                logger.info("%s file queued for processing", file_key)

        # Add to the audit table (regardless of whether it is a duplicate)
        dynamodb_client.put_item(
            TableName=AUDIT_TABLE_NAME,
            Item={
                AuditTableKeys.MESSAGE_ID: {"S": message_id},
                AuditTableKeys.FILENAME: {"S": file_key},
                AuditTableKeys.QUEUE_NAME: {"S": queue_name},
                AuditTableKeys.STATUS: {"S": file_status},
                AuditTableKeys.TIMESTAMP: {"S": created_at_formatted_str},
            },
            ConditionExpression="attribute_not_exists(message_id)",  # Prevents accidental overwrites
        )
        logger.info("%s file, with message id %s, successfully added to audit table", file_key, message_id)

        # Return a bool indicating whether the file status is queued
        return True if file_status == FileStatus.QUEUED else False

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error
