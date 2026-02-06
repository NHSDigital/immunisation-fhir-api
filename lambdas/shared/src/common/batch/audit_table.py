from datetime import datetime
from typing import Optional, Tuple

from common.clients import get_dynamodb_client, logger
from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys, audit_table_key_data_types_map
from common.models.errors import UnhandledAuditTableError

ITEM_EXISTS_CONDITION_EXPRESSION = f"attribute_exists({AuditTableKeys.MESSAGE_ID})"
NOTHING_TO_UPDATE_ERROR_MESSAGE = "Improper usage: you must provide at least one attribute to update"

dynamodb_client = get_dynamodb_client()


def create_audit_table_item(
    message_id: str,
    file_key: str,
    created_at_formatted_str: str,
    expiry_timestamp: int,
    queue_name: str,
    file_status: str,
    error_details: Optional[str] = None,
) -> None:
    """
    Creates an audit table item with the file details
    """
    audit_item = {
        AuditTableKeys.MESSAGE_ID: {audit_table_key_data_types_map[AuditTableKeys.MESSAGE_ID]: message_id},
        AuditTableKeys.FILENAME: {audit_table_key_data_types_map[AuditTableKeys.FILENAME]: file_key},
        AuditTableKeys.QUEUE_NAME: {audit_table_key_data_types_map[AuditTableKeys.QUEUE_NAME]: queue_name},
        AuditTableKeys.STATUS: {audit_table_key_data_types_map[AuditTableKeys.STATUS]: file_status},
        AuditTableKeys.TIMESTAMP: {audit_table_key_data_types_map[AuditTableKeys.TIMESTAMP]: created_at_formatted_str},
        AuditTableKeys.EXPIRES_AT: {audit_table_key_data_types_map[AuditTableKeys.EXPIRES_AT]: str(expiry_timestamp)},
    }

    if error_details is not None:
        audit_item[AuditTableKeys.ERROR_DETAILS] = {
            audit_table_key_data_types_map[AuditTableKeys.ERROR_DETAILS]: error_details
        }

    try:
        dynamodb_client.put_item(TableName=AUDIT_TABLE_NAME, Item=audit_item)
    except Exception as error:
        logger.error(error)
        raise UnhandledAuditTableError(error) from error

    logger.info(
        "%s file, with message id %s, successfully added to audit table",
        file_key,
        message_id,
    )


def update_audit_table_item(
    file_key: str,
    message_id: str,
    attrs_to_update: dict[AuditTableKeys, any],
) -> None:
    """Updates an item in the audit table with the requested values"""
    if attrs_to_update is None or len(attrs_to_update) == 0:
        logger.error(NOTHING_TO_UPDATE_ERROR_MESSAGE)
        raise ValueError(NOTHING_TO_UPDATE_ERROR_MESSAGE)

    update_expression, expression_attr_names, expression_attr_values = _build_ddb_update_parameters(attrs_to_update)
    try:
        dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {audit_table_key_data_types_map[AuditTableKeys.MESSAGE_ID]: message_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ConditionExpression=ITEM_EXISTS_CONDITION_EXPRESSION,
        )
    except Exception as error:
        logger.error(error)
        raise UnhandledAuditTableError(error) from error

    logger.info(_build_audit_table_update_log_message(file_key, message_id, attrs_to_update))


def _build_ddb_update_parameters(
    attrs_to_update: dict[AuditTableKeys, any],
) -> Tuple[str, dict[str, any], dict[str, any]]:
    """Assembles an UpdateExpression, ExpressionAttributeNames and ExpressionAttributeValues for the DynamoDB Update"""
    update_expression = "SET "
    expression_attr_names = {}
    expression_attr_values = {}

    for audit_table_key, value in attrs_to_update.items():
        element = f"#{audit_table_key} = :{audit_table_key}"
        update_expression = (
            update_expression + element if update_expression == "SET " else update_expression + ", " + element
        )

        expression_attr_names[f"#{audit_table_key}"] = audit_table_key
        expression_attr_values[f":{audit_table_key}"] = {audit_table_key_data_types_map[audit_table_key]: str(value)}

    return update_expression, expression_attr_names, expression_attr_values


def _build_audit_table_update_log_message(file_key: str, message_id: str, attrs_to_update: dict[AuditTableKeys, any]):
    list_of_updates_str = ", ".join(
        f"{attr} = {str(value)}" for attr, value in attrs_to_update.items() if attr is not AuditTableKeys.ERROR_DETAILS
    )

    return (
        "Attributes for file "
        + f"{file_key}"
        + " with message_id "
        + f"{message_id}"
        + " successfully updated in the audit table: "
        + list_of_updates_str
    )


def get_ingestion_start_time_by_message_id(event_message_id: str) -> int:
    """Retrieves ingestion start time by unique event message ID"""
    # Required by JSON ack file
    audit_record = dynamodb_client.get_item(
        TableName=AUDIT_TABLE_NAME, Key={AuditTableKeys.MESSAGE_ID: {"S": event_message_id}}
    )

    ingestion_start_time_str = audit_record.get("Item", {}).get(AuditTableKeys.INGESTION_START_TIME, {}).get("S")
    if not ingestion_start_time_str:
        return 0
    try:
        ingestion_start_time = int(
            (datetime.strptime(ingestion_start_time_str, "%Y%m%dT%H%M%S00") - datetime(1970, 1, 1)).total_seconds()
        )
    except ValueError:
        return 0
    return ingestion_start_time


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
            ConditionExpression=ITEM_EXISTS_CONDITION_EXPRESSION,
            ReturnValues="UPDATED_NEW",
        )
    except Exception as error:
        logger.error(error)
        raise UnhandledAuditTableError(error) from error
