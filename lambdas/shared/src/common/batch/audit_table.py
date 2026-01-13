import time
from typing import Optional

from common.clients import get_dynamodb_client, logger
from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys
from common.models.errors import UnhandledAuditTableError

FILE_EXISTS_CONDITION_EXPRESSION = f"attribute_exists({AuditTableKeys.MESSAGE_ID})"
FILE_DOES_NOT_EXIST_CONDITION_EXPRESSION = f"attribute_not_exists({AuditTableKeys.MESSAGE_ID})"


def create_audit_table_item(
    message_id: str,
    file_key: str,
    created_at_formatted_str: str,
    expiry_timestamp: int,
    queue_name: str,
    file_status: str,
    error_details: Optional[str] = None,
    condition_expression: Optional[str] = None,
) -> None:
    """
    Creates an audit table item with the file details
    """
    audit_item = {
        AuditTableKeys.MESSAGE_ID: {"S": message_id},
        AuditTableKeys.FILENAME: {"S": file_key},
        AuditTableKeys.QUEUE_NAME: {"S": queue_name},
        AuditTableKeys.STATUS: {"S": file_status},
        AuditTableKeys.TIMESTAMP: {"S": created_at_formatted_str},
        AuditTableKeys.EXPIRES_AT: {"N": str(expiry_timestamp)},
    }

    if error_details is not None:
        audit_item[AuditTableKeys.ERROR_DETAILS] = {"S": error_details}

    try:
        # Add to the audit table (regardless of whether it is a duplicate)
        if not condition_expression:
            get_dynamodb_client().put_item(
                TableName=AUDIT_TABLE_NAME,
                Item=audit_item,
            )
        else:
            get_dynamodb_client().put_item(
                TableName=AUDIT_TABLE_NAME,
                Item=audit_item,
                ConditionExpression=condition_expression,
            )
        logger.info(
            "%s file, with message id %s, successfully added to audit table",
            file_key,
            message_id,
        )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error


def update_audit_table_item(
    file_key: str,
    message_id: str,
    status: Optional[str] = None,
    ingestion_start_time: Optional[float] = None,
    ingestion_end_time: Optional[str] = None,
    error_details: Optional[str] = None,
    record_count: Optional[int] = None,
    records_succeeded: Optional[int] = None,
) -> None:
    """Updates an item in the audit table with the requested values"""
    # TODO: tidy up duplicated code into helper func. Maybe loop through optional args
    updated_attributes = {}
    expression_attr_names = {}
    expression_attr_values = {}

    if status is not None:
        updated_attributes[AuditTableKeys.STATUS] = status
        expression_attr_names = {f"#{AuditTableKeys.STATUS}": AuditTableKeys.STATUS}
        expression_attr_values = {f":{AuditTableKeys.STATUS}": {"S": status}}

    if ingestion_start_time is not None:
        ingestion_start_time_str = time.strftime("%Y%m%dT%H%M%S00", time.gmtime(ingestion_start_time))

        updated_attributes[AuditTableKeys.INGESTION_START_TIME] = ingestion_start_time_str
        expression_attr_names = {f"#{AuditTableKeys.INGESTION_START_TIME}": AuditTableKeys.INGESTION_START_TIME}
        expression_attr_values = {f":{AuditTableKeys.INGESTION_START_TIME}": {"S": ingestion_start_time_str}}

    if ingestion_end_time is not None:
        updated_attributes[AuditTableKeys.INGESTION_END_TIME] = ingestion_end_time
        expression_attr_names = {f"#{AuditTableKeys.INGESTION_END_TIME}": AuditTableKeys.INGESTION_END_TIME}
        expression_attr_values = {f":{AuditTableKeys.INGESTION_END_TIME}": {"S": ingestion_end_time}}

    if record_count is not None:
        updated_attributes[AuditTableKeys.RECORD_COUNT] = record_count
        expression_attr_names[f"#{AuditTableKeys.RECORD_COUNT}"] = AuditTableKeys.RECORD_COUNT
        expression_attr_values[f":{AuditTableKeys.RECORD_COUNT}"] = {"N": str(record_count)}

    if records_succeeded is not None:
        updated_attributes[AuditTableKeys.RECORDS_SUCCEEDED] = records_succeeded
        expression_attr_names[f"#{AuditTableKeys.RECORDS_SUCCEEDED}"] = AuditTableKeys.RECORDS_SUCCEEDED
        expression_attr_values[f":{AuditTableKeys.RECORDS_SUCCEEDED}"] = {"N": str(records_succeeded)}

    if error_details is not None:
        updated_attributes[AuditTableKeys.ERROR_DETAILS] = error_details
        expression_attr_names[f"#{AuditTableKeys.ERROR_DETAILS}"] = AuditTableKeys.ERROR_DETAILS
        expression_attr_values[f":{AuditTableKeys.ERROR_DETAILS}"] = {"S": error_details}

    try:
        update_expression = "SET " + ", ".join(f"#{attr} = :{attr}" for attr in updated_attributes.keys())

        dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ConditionExpression=FILE_EXISTS_CONDITION_EXPRESSION,
        )

        for attr_name, attr_value in updated_attributes.items():
            if attr_name is AuditTableKeys.ERROR_DETAILS:
                continue

            logger.info(
                "The %s of file %s, with message id %s, was successfully updated to %s in the audit table",
                attr_name,
                file_key,
                message_id,
                str(attr_value),
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
            ConditionExpression=FILE_EXISTS_CONDITION_EXPRESSION,
            ReturnValues="UPDATED_NEW",
        )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error
