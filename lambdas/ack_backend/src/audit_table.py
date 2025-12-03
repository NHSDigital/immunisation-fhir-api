"""Add the filename to the audit table and check for duplicates."""

from typing import Optional

from common.clients import dynamodb_client, logger
from common.models.errors import UnhandledAuditTableError
from constants import AUDIT_TABLE_NAME, AuditTableKeys, FileStatus


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
        TableName=AUDIT_TABLE_NAME, Key={AuditTableKeys.MESSAGE_ID: {"S": event_message_id}}
    )

    record_count = audit_record.get("Item", {}).get(AuditTableKeys.RECORD_COUNT, {}).get("N")

    if not record_count:
        return None

    return int(record_count)


def set_record_success_count(message_id: str) -> Optional[int]:
    """Set the 'records_succeeded' item in the audit table entry"""
    audit_record = dynamodb_client.get_item(
        TableName=AUDIT_TABLE_NAME, Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}}
    )
    record_count_item = audit_record.get("Item", {}).get(AuditTableKeys.RECORD_COUNT, {}).get("N")
    records_failed_item = audit_record.get("Item", {}).get(AuditTableKeys.RECORDS_FAILED, {}).get("N")

    record_count = int(record_count_item) if record_count_item else 0
    records_failed = int(records_failed_item) if records_failed_item else 0
    records_succeeded = record_count - records_failed

    try:
        response = dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
            UpdateExpression="SET #counter = :value",
            ExpressionAttributeNames={"#counter": AuditTableKeys.RECORDS_SUCCEEDED},
            ExpressionAttributeValues={":value": {"S": str(records_succeeded)}},
            ConditionExpression="attribute_exists(message_id)",
            ReturnValues="UPDATED_NEW",
        )
        logger.info(
            "Counter %s for message id %s set to %s in the audit table",
            AuditTableKeys.RECORDS_SUCCEEDED,
            message_id,
            response.get("Attributes", {}).get(AuditTableKeys.RECORDS_SUCCEEDED),
        )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error


def increment_record_counter(message_id: str, counter_name: str = AuditTableKeys.RECORDS_FAILED) -> None:
    """
    Increment a counter attribute safely, handling the case where it might not exist.
    From https://docs.aws.amazon.com/code-library/latest/ug/dynamodb_example_dynamodb_Scenario_AtomicCounterOperations_section.html
    """

    increment_value = 1
    initial_value = 0
    try:
        # Use SET with if_not_exists to safely increment the counter
        response = dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
            UpdateExpression="SET #counter = if_not_exists(#counter, :initial) + :increment",
            ExpressionAttributeNames={"#counter": counter_name},
            ExpressionAttributeValues={":increment": {"S": str(increment_value)}, ":initial": {"S": str(initial_value)}},
            ConditionExpression="attribute_exists(message_id)",
            ReturnValues="UPDATED_NEW",
        )
        logger.info(
            "Counter %s for message id %s incremented to %s in the audit table",
            counter_name,
            message_id,
            response.get("Attributes", {}).get(counter_name),
        )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error
