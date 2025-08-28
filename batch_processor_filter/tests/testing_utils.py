import json

from aws_lambda_typing.events.sqs import SQSMessage
from batch_file_created_event import BatchFileCreatedEvent


MOCK_ENVIRONMENT_DICT = {
    "AUDIT_TABLE_NAME": "immunisation-batch-internal-dev-audit-table",
    "QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/imms-batch-metadata-queue.fifo",
    "FILE_NAME_GSI": "filename_index",
    "QUEUE_NAME_GSI": "queue_name_index"
}


def make_sqs_record(batch_file_created_event: BatchFileCreatedEvent) -> SQSMessage:
    # For brevity, we are not including all the fields. The app code only requires the body
    return {
        "messageId": "1234",
        "eventSource": "aws:sqs",
        "body": json.dumps(batch_file_created_event)
    }


def add_entry_to_mock_table(dynamodb_client, table_name: str, batch_file_created_event: BatchFileCreatedEvent,
                            status: str) -> None:
    """Add an entry to the audit table"""
    audit_table_entry = {
        "message_id": {"S": batch_file_created_event.get("message_id")},
        "queue_name": {"S": f'{batch_file_created_event["supplier"]}_{batch_file_created_event["vaccine_type"]}'},
        "filename": {"S": batch_file_created_event.get("filename")},
        "status": {"S": status}
    }
    dynamodb_client.put_item(TableName=table_name, Item=audit_table_entry)


def get_audit_entry_status_by_id(dynamodb_client, table_name: str, audit_entry_id: str) -> str | None:
    audit_entry = dynamodb_client.get_item(
        TableName=table_name, Key={"message_id": {"S": audit_entry_id}}
    ).get("Item", {})

    return audit_entry.get("status", {}).get("S")
