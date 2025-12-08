"""Add the filename to the audit table and check for duplicates."""

import time
from typing import Optional

from common.clients import dynamodb_client, logger
from common.models.errors import UnhandledAuditTableError
from constants import AUDIT_TABLE_NAME, AuditTableKeys


def update_audit_table_status(
    file_key: str,
    message_id: str,
    status: str,
    error_details: Optional[str] = None,
    record_count: Optional[int] = None,
) -> None:
    """Updates the status in the audit table to the requested value"""
    update_expression = f"SET #{AuditTableKeys.STATUS} = :{AuditTableKeys.STATUS}"
    expression_attr_names = {f"#{AuditTableKeys.STATUS}": AuditTableKeys.STATUS}
    expression_attr_values = {f":{AuditTableKeys.STATUS}": {"S": status}}

    if record_count is not None:
        update_expression = update_expression + f", #{AuditTableKeys.RECORD_COUNT} = :{AuditTableKeys.RECORD_COUNT}"
        expression_attr_names[f"#{AuditTableKeys.RECORD_COUNT}"] = AuditTableKeys.RECORD_COUNT
        expression_attr_values[f":{AuditTableKeys.RECORD_COUNT}"] = {"N": str(record_count)}

    if error_details is not None:
        update_expression = update_expression + f", #{AuditTableKeys.ERROR_DETAILS} = :{AuditTableKeys.ERROR_DETAILS}"
        expression_attr_names[f"#{AuditTableKeys.ERROR_DETAILS}"] = AuditTableKeys.ERROR_DETAILS
        expression_attr_values[f":{AuditTableKeys.ERROR_DETAILS}"] = {"S": error_details}

    try:
        # Update the status in the audit table to "Processed"
        dynamodb_client.update_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": message_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ConditionExpression=f"attribute_exists({AuditTableKeys.MESSAGE_ID})",
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


def set_audit_table_ingestion_start_time(
    file_key: str,
    message_id: str,
    start_time: float,
) -> None:
    """Sets the ingestion_start_time in the audit table to the requested time"""
    # format the time
    ingestion_start_time = time.strftime("%Y%m%dT%H%M%S00", time.gmtime(start_time))

    update_expression = f"SET #{AuditTableKeys.INGESTION_START_TIME} = :{AuditTableKeys.INGESTION_START_TIME}"
    expression_attr_names = {f"#{AuditTableKeys.INGESTION_START_TIME}": AuditTableKeys.INGESTION_START_TIME}
    expression_attr_values = {f":{AuditTableKeys.INGESTION_START_TIME}": {"S": ingestion_start_time}}

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
        result = response.get("Attributes", {}).get(AuditTableKeys.INGESTION_START_TIME).get("S")
        logger.info(
            "ingestion_start_time for %s file, with message id %s, was successfully updated to %s in the audit table",
            file_key,
            message_id,
            result,
        )

    except Exception as error:  # pylint: disable = broad-exception-caught
        logger.error(error)
        raise UnhandledAuditTableError(error) from error
