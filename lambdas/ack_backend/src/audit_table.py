"""Add the filename to the audit table and check for duplicates."""

import time
from typing import Optional

from common.clients import dynamodb_client, logger
from common.models.errors import UnhandledAuditTableError
from constants import AUDIT_TABLE_NAME, AuditTableKeys, FileStatus

CONDITION_EXPRESSION = "attribute_exists(message_id)"


def change_audit_table_status_to_processed(file_key: str, message_id: str) -> None:
    """Updates the status in the audit table to 'Processed' and returns the queue name."""
    try:
        # Update the status in the audit table to "Processed"
        response = dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": {"S": FileStatus.PROCESSED}},
            ConditionExpression=CONDITION_EXPRESSION,
            ReturnValues="UPDATED_NEW",
        )
        result = response.get("Attributes", {}).get("status").get("S")
        logger.info(
            "The status of %s file, with message id %s, was successfully updated to %s in the audit table",
            file_key,
            message_id,
            result,
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


def set_records_succeeded_count(message_id: str) -> None:
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
            UpdateExpression="SET #attribute = :value",
            ExpressionAttributeNames={"#attribute": AuditTableKeys.RECORDS_SUCCEEDED},
            ExpressionAttributeValues={":value": {"N": str(records_succeeded)}},
            ConditionExpression=CONDITION_EXPRESSION,
            ReturnValues="UPDATED_NEW",
        )
        result = response.get("Attributes", {}).get(AuditTableKeys.RECORDS_SUCCEEDED).get("N")
        logger.info(
            "Attribute %s for message id %s set to %s in the audit table",
            AuditTableKeys.RECORDS_SUCCEEDED,
            message_id,
            result,
        )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error


def increment_records_failed_count(message_id: str) -> None:
    """
    Increment a counter attribute safely, handling the case where it might not exist.
    From https://docs.aws.amazon.com/code-library/latest/ug/dynamodb_example_dynamodb_Scenario_AtomicCounterOperations_section.html
    """

    increment_value = 1
    initial_value = 0
    try:
        # Use SET with if_not_exists to safely increment the counter attribute
        dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
            UpdateExpression="SET #attribute = if_not_exists(#attribute, :initial) + :increment",
            ExpressionAttributeNames={"#attribute": AuditTableKeys.RECORDS_FAILED},
            ExpressionAttributeValues={":increment": {"N": str(increment_value)}, ":initial": {"N": str(initial_value)}},
            ConditionExpression=CONDITION_EXPRESSION,
            ReturnValues="UPDATED_NEW",
        )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error


def set_audit_table_ingestion_end_time(
    file_key: str,
    message_id: str,
    complete_time: float,
) -> None:
    """Sets the ingestion_end_time in the audit table to the requested time"""
    # format the time
    ingestion_end_time = time.strftime("%Y%m%dT%H%M%S00", time.gmtime(complete_time))

    update_expression = f"SET #{AuditTableKeys.INGESTION_END_TIME} = :{AuditTableKeys.INGESTION_END_TIME}"
    expression_attr_names = {f"#{AuditTableKeys.INGESTION_END_TIME}": AuditTableKeys.INGESTION_END_TIME}
    expression_attr_values = {f":{AuditTableKeys.INGESTION_END_TIME}": {"S": ingestion_end_time}}

    try:
        response = dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ConditionExpression=f"attribute_exists({AuditTableKeys.MESSAGE_ID})",
            ReturnValues="UPDATED_NEW",
        )
        result = response.get("Attributes", {}).get(AuditTableKeys.INGESTION_END_TIME).get("S")
        logger.info(
            "ingestion_end_time for %s file, with message id %s, was successfully updated to %s in the audit table",
            file_key,
            message_id,
            result,
        )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error
