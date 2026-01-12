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
