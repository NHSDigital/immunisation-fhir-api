from typing import Optional

from common.clients import get_dynamodb_client, logger
from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys, audit_table_key_data_types_map
from common.models.errors import UnhandledAuditTableError

ITEM_EXISTS_CONDITION_EXPRESSION = f"attribute_exists({AuditTableKeys.MESSAGE_ID})"
ITEM_DOES_NOT_EXIST_CONDITION_EXPRESSION = f"attribute_not_exists({AuditTableKeys.MESSAGE_ID})"

dynamodb_client = get_dynamodb_client()


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
        # Add to the audit table (regardless of whether it is a duplicate)
        if not condition_expression:
            dynamodb_client.put_item(
                TableName=AUDIT_TABLE_NAME,
                Item=audit_item,
            )
        else:
            dynamodb_client.put_item(
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
    optional_params: dict[AuditTableKeys, any],
) -> None:
    """Updates an item in the audit table with the requested values"""
    update_expression = "SET "
    expression_attr_names = {}
    expression_attr_values = {}

    for audit_table_key, value in optional_params.items():
        update_expression = _build_update_expression_attribute_names_and_values(
            key=audit_table_key,
            value=value,
            update_expression=update_expression,
            expression_attr_names=expression_attr_names,
            expression_attr_values=expression_attr_values,
        )
    try:
        dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {audit_table_key_data_types_map[AuditTableKeys.MESSAGE_ID]: message_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ConditionExpression=ITEM_EXISTS_CONDITION_EXPRESSION,
        )

        for audit_table_key, value in optional_params.items():
            if audit_table_key is AuditTableKeys.ERROR_DETAILS:
                continue

            logger.info(
                "The %s of file %s, with message id %s, was successfully updated to %s in the audit table",
                audit_table_key,
                file_key,
                message_id,
                str(value),
            )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error


def _build_update_expression_attribute_names_and_values(
    key: str, value: any, update_expression: str, expression_attr_names: dict, expression_attr_values: dict
) -> str:
    """Assembles an UpdateExpression, ExpressionAttributeNames and ExpressionAttributeValues"""
    element = f"#{key} = :{key}"
    update_expression = (
        update_expression + element if update_expression == "SET " else update_expression + ", " + element
    )

    expression_attr_names[f"#{key}"] = key
    expression_attr_values[f":{key}"] = {audit_table_key_data_types_map[key]: str(value)}

    return update_expression


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

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error
