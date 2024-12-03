"""Add the filename to the audit table and check for duplicates."""

import os
import logging
from boto3.dynamodb.conditions import Key
from clients import dynamodb_client, dynamodb_resource


logger = logging.getLogger()


def add_to_audit_table(message_id: str, file_key: str, created_at_formatted_str: str) -> bool:
    """
    Add the filename to the audit table.
    Raises an error if the file is a duplicate (after adding it to the audit table).
    """
    try:
        table_name = os.environ["AUDIT_TABLE_NAME"]
        file_name_gsi = os.environ["FILE_NAME_GSI"]

        # Check for duplicates before adding to the table (if the query returns any items, then the file is a duplicate)
        file_name_response = dynamodb_resource.Table(table_name).query(
            IndexName=file_name_gsi, KeyConditionExpression=Key("filename").eq(file_key)
        )

        duplicate_exists = bool(file_name_response.get("Items"))

        # Add to the audit table (regardless of where it is a duplicate)
        dynamodb_client.put_item(
            TableName=table_name,
            Item={
                "message_id": {"S": message_id},
                "filename": {"S": file_key},
                "status": {"S": "Processed"},
                "timestamp": {"S": created_at_formatted_str},
            },
            ConditionExpression="attribute_not_exists(message_id)",  # Prevents accidental overwrites
        )
        logger.info("%s file, with message id %s, successfully added to audit table", file_key, message_id)

        # If a duplicte exists, raise an exception
        if duplicate_exists:
            logger.error("%s file duplicate added to s3 at the following time: %s", file_key, created_at_formatted_str)
            raise Exception(f"Duplicate file: {file_key}")

        return not duplicate_exists

    except Exception:  # pylint: disable = broad-exception-caught
        return False
