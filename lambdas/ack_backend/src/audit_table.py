"""Add the filename to the audit table and check for duplicates."""

from common.clients import dynamodb_client, logger
from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys, FileStatus
from common.models.errors import UnhandledAuditTableError

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


def get_record_count_and_failures_by_message_id(event_message_id: str) -> tuple[int, int]:
    """Retrieves total record count and total failures by unique event message ID"""
    audit_record = dynamodb_client.get_item(
        TableName=AUDIT_TABLE_NAME, Key={AuditTableKeys.MESSAGE_ID: {"S": event_message_id}}
    )

    record_count = audit_record.get("Item", {}).get(AuditTableKeys.RECORD_COUNT, {}).get("N")
    failures_count = audit_record.get("Item", {}).get(AuditTableKeys.RECORDS_FAILED, {}).get("N")

    return int(record_count) if record_count else 0, int(failures_count) if failures_count else 0


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


def set_audit_record_success_count_and_end_time(
    file_key: str, message_id: str, success_count: int, ingestion_end_time: str
) -> None:
    """Sets the 'records_succeeded' and 'ingestion_end_time' attributes for the given audit record"""
    update_expression = (
        f"SET #{AuditTableKeys.INGESTION_END_TIME} = :{AuditTableKeys.INGESTION_END_TIME}"
        f", #{AuditTableKeys.RECORDS_SUCCEEDED} = :{AuditTableKeys.RECORDS_SUCCEEDED}"
    )
    expression_attr_names = {
        f"#{AuditTableKeys.INGESTION_END_TIME}": AuditTableKeys.INGESTION_END_TIME,
        f"#{AuditTableKeys.RECORDS_SUCCEEDED}": AuditTableKeys.RECORDS_SUCCEEDED,
    }
    expression_attr_values = {
        f":{AuditTableKeys.INGESTION_END_TIME}": {"S": ingestion_end_time},
        f":{AuditTableKeys.RECORDS_SUCCEEDED}": {"N": str(success_count)},
    }

    try:
        dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ConditionExpression=CONDITION_EXPRESSION,
        )
    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error

    logger.info(
        "ingestion_end_time for %s file, with message id %s, was successfully updated to %s in the audit table",
        file_key,
        message_id,
        ingestion_end_time,
    )
    logger.info(
        "records_succeeded for %s file, with message id %s, was successfully updated to %s in the audit table",
        file_key,
        message_id,
        str(success_count),
    )
