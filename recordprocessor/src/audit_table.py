"""Add the filename to the audit table and check for duplicates."""

import os
from typing import Union
from boto3.dynamodb.conditions import Key
from clients import dynamodb_client, dynamodb_resource, logger
from errors import UnhandledAuditTableError


# TODO update the function name in filename, ack lambda and ecs task
def update_audit_table_status(file_key: str) -> None:
    """
    Update the status in the audit table.
    """
    try:
        table_name = os.environ["AUDIT_TABLE_NAME"]
        file_name_gsi = "filename_index"
        file_name_response = dynamodb_resource.Table(table_name).query(
            IndexName=file_name_gsi, KeyConditionExpression=Key("filename").eq(file_key)
        )
        items = file_name_response.get("Items", [])
        message_id = items[0].get("message_id")
        queue_name = items[0].get("queue_name")
        # Add to the audit table
        dynamodb_client.update_item(
            TableName=table_name,
            Key={"message_id": {"S": message_id}},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": {"S": "Processed"}},
            ConditionExpression="attribute_exists(message_id)",
        )
        logger.info(
            "%s file, with message id %s, and the status successfully updated to audit table",
            file_key,
            message_id,
        )
        return queue_name
    except Exception as error:  # pylint: disable = broad-exception-caught
        error_message = error  # f"Error adding {file_key} to the audit table"
        logger.error(error_message)
        raise UnhandledAuditTableError(error_message) from error


def get_queued_file_details(
    queue_name: str,
) -> tuple[Union[None, str], Union[None, str]]:
    """
    Check for queued files which return none or oldest file queued for processing.
    Returns a tuple in the format (file_name, message_id) for the oldest file.
    Defaults to (none,none) if no file found in queued status
    """
    table_name = os.environ["AUDIT_TABLE_NAME"]
    queue_name_gsi = "queue_name_index"

    queue_response = dynamodb_resource.Table(table_name).query(
        IndexName=queue_name_gsi,
        KeyConditionExpression=Key("queue_name").eq(queue_name)
        & Key("status").eq("Queued"),
    )
    if queue_response["Items"]:
        file_name, message_id = get_file_name(queue_response)
        return file_name, message_id
    else:
        return None, None


def get_file_name(queue_response: dict) -> tuple[str, str]:
    """
    Returns (file_name, message_id) for the oldest file.
    """
    sorted_item = sorted(queue_response["Items"], key=lambda x: x["timestamp"])
    first_record = sorted_item[0]
    file_name = first_record.get("filename")
    message_id = first_record.get("message_id")
    return file_name, message_id
