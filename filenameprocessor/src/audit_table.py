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
        raise DuplicateFileError(f"Duplicate file: {file_key}")


def upsert_audit_table(
    message_id: str,
    file_key: str,
    created_at_formatted_str: str,
    queue_name: str,
    file_status: str,
    is_existing_file: bool,
) -> bool:
    """
    Updates the audit table with the file details. Returns a bool indicating whether the file is ready to process
    (i.e. if the file has passed initial validation and there are no other files in the queue, then the file is ready
    to be sent for row level processing.)
    """
    try:
        # If the file is not new, then the lambda has been invoked by the next file in the queue for processing
        if is_existing_file:
            dynamodb_client.update_item(
                TableName=AUDIT_TABLE_NAME,
                Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
                UpdateExpression="SET #status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": {"S": FileStatus.PROCESSING}},
                ConditionExpression="attribute_exists(message_id)",
            )
            logger.info("%s file set for processing, and the status successfully updated in audit table", file_key)
            return True

        # If the file is not already processed, check whether there is a file ahead in the queue already processing
        file_in_same_queue_already_processing = False
        if not file_status.eq(FileStatus.PROCESSED):
            queue_response = dynamodb_resource.Table(AUDIT_TABLE_NAME).query(
                IndexName=AUDIT_TABLE_QUEUE_NAME_GSI,
                KeyConditionExpression=Key(AuditTableKeys.QUEUE_NAME).eq(queue_name)
                & Key(AuditTableKeys.STATUS).eq(FileStatus.PROCESSING),
            )
            if queue_response["Items"]:
                file_status = FileStatus.QUEUED
                logger.info("%s file queued for processing: %s", file_key)
                file_in_same_queue_already_processing = True

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

        # If processing exists for supplier_vaccine, return false as this file must queue for processing
        return False if file_in_same_queue_already_processing else True

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error
