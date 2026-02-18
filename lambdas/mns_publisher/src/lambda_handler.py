import json
from typing import Optional, Tuple

from aws_lambda_typing import context, events

from common.clients import logger
from create_notification import create_mns_notification


def lambda_handler(event: events.SQSEvent, _: context.Context) -> dict:
    event_records = event.get("Records", [])
    failed_message_ids = []

    for record in event_records:
        message_id, immunisation_id = extract_trace_ids(record)
        notification_id = None

        try:
            notification = create_mns_notification(record)
            notification_id = notification.get("id", None)  # generated UUID for MNS
            logger.info("Processing message", trace_id=notification_id)

            # TODO: Send notification to MNS API
            # publish_to_mns(notification)

            logger.info(
                "Successfully created MNS notification",
                trace_id={
                    "mns_notification_id": notification_id,
                },
            )

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
            failed_message_ids.append({"itemIdentifier": message_id})

    if failed_message_ids:
        logger.warning(f"Batch completed with {len(failed_message_ids)} failures")
    else:
        logger.info(f"Successfully processed all {len(event_records)} messages")

    return {"batchItemFailures": failed_message_ids}


def extract_trace_ids(record: dict) -> Tuple[str, Optional[str]]:
    """
    Extract identifiers for tracing from SQS record.
    Returns: Tuple of (message_id, immunisation_id)
    """
    message_id = record.get("messageId", "unknown")
    immunisation_id = None

    try:
        body = record.get("body", {})
        if isinstance(body, str):
            body = json.loads(body)

        immunisation_id = body.get("dynamodb", {}).get("NewImage", {}).get("ImmsID", {}).get("S")
    except Exception as e:
        logger.warning(f"Could not extract immunisation_id: {message_id}: {e}")

    return message_id, immunisation_id
