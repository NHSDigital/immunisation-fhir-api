"""Add the filename to the audit table and check for duplicates."""

from typing import Optional

from clients import dynamodb_client, logger
from errors import UnhandledAuditTableError
from constants import AUDIT_TABLE_NAME, AuditTableKeys


def update_audit_table_status(file_key: str, message_id: str, status: str, error_details: Optional[str] = None) -> None:
    """Updates the status in the audit table to the requested value"""
    update_expression = f"SET #{AuditTableKeys.STATUS} = :status"
    expression_attr_names = {f"#{AuditTableKeys.STATUS}": "status"}
    expression_attr_values = {":status": {"S": status}}

    if error_details is not None:
        update_expression = update_expression + f", #{AuditTableKeys.ERROR_DETAILS} = :error_details"
        expression_attr_names[f"#{AuditTableKeys.ERROR_DETAILS}"] = "error_details"
        expression_attr_values[":error_details"] = {"S": error_details}

    try:
        # Update the status in the audit table to "Processed"
        dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ConditionExpression="attribute_exists(message_id)",
        )

        logger.info(
            "The status of %s file, with message id %s, was successfully updated to %s in the audit table",
            file_key,
            message_id,
            status,
        )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error
