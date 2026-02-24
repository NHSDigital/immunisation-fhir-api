import json
import os
from typing import Tuple

from aws_lambda_typing import events
from aws_lambda_typing.events.sqs import SQSMessage

from common.api_clients.mns_setup import get_mns_service
from common.clients import logger
from create_notification import create_mns_notification

mns_env = os.getenv("MNS_ENV", "int")


def process_records(records: events.SQSEvent) -> list[dict]:
    """
    Process multiple SQS records.
    Args: records: List of SQS records to process
    Returns: List of failed item identifiers for partial batch failure
    """
    batch_item_failures = []
    mns_service = get_mns_service(mns_env=mns_env)

    for record in records:
        failed_batch_item = process_record(record, mns_service)
        if failed_batch_item:
            batch_item_failures.append(failed_batch_item)

    return batch_item_failures


def process_record(record: SQSMessage, mns_service) -> dict | None:
    """
    Process a single SQS record.
    Args:
        record: SQS record containing DynamoDB stream data
        mns_service: MNS service instance for publishing
    Returns: Failure dict with itemIdentifier if processing failed, None if successful
    """
    message_id, immunisation_id = extract_trace_ids(record)
    notification_id = None

    try:
        # Create notification payload
        mns_notification_payload = create_mns_notification(record)
        notification_id = mns_notification_payload.get("id")
        action_flag = mns_notification_payload.get("filtering", {}).get("action")
        logger.info(
            "Processing message",
            trace_ids={
                "notification_id": notification_id,
                "message_id": message_id,
                "immunisation_id": immunisation_id,
                "action_flag": action_flag,
            },
        )

        # Publish to MNS
        mns_pub_response = mns_service.publish_notification(mns_notification_payload)
        if mns_pub_response["status_code"] != 200:
            raise RuntimeError("MNS publish failed")
        logger.info("Successfully created MNS notification", trace_ids={"mns_notification_id": notification_id})

        return None

    except Exception as e:
        logger.exception(
            "Failed to process message",
            trace_ids={
                "message_id": message_id,
                "immunisation_id": immunisation_id,
                "mns_notification_id": notification_id,
                "error": str(e),
            },
        )
        return {"itemIdentifier": message_id}


def extract_trace_ids(record: SQSMessage) -> Tuple[str, str | None]:
    """
    Extract identifiers for tracing from SQS record.
    Returns: Tuple of (message_id, immunisation_id)
    """
    sqs_message_id = record.get("messageId", "unknown")
    immunisation_id = None

    try:
        sqs_event_body = record.get("body", {})
        if isinstance(sqs_event_body, str):
            sqs_event_body = json.loads(sqs_event_body)

        immunisation_id = sqs_event_body.get("dynamodb", {}).get("NewImage", {}).get("ImmsID", {}).get("S")
    except Exception as e:
        logger.warning(f"Could not extract immunisation_id: {immunisation_id}: {e}")

    return sqs_message_id, immunisation_id
