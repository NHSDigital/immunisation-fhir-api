import json
import os
from typing import Tuple

from aws_lambda_typing import context, events
from aws_lambda_typing.events.sqs import SQSMessage

from common.api_clients.mns_setup import get_mns_service
from common.clients import logger
from create_notification import create_mns_notification

apigee_env = os.getenv("APIGEE_ENVIRONMENT", "int")


def lambda_handler(event: events.SQSEvent, _: context.Context) -> dict[str, list]:
    event_records = event.get("Records", [])
    batch_item_failures = []

    for record in event_records:
        message_id, immunisation_id = extract_trace_ids(record)
        notification_id = None

        try:
            mns_notification_payload = create_mns_notification(record)
            notification_id = mns_notification_payload.get("id", None)  # generated UUID for MNS
            action_flag = mns_notification_payload.get("action")
            logger.info(
                "Processing message",
                trace_ids={
                    "notification_id": notification_id,
                    "message_id": message_id,
                    "immunisation_id": immunisation_id,
                    "action_flag": action_flag,
                },
            )

            mns_service = get_mns_service(mns=apigee_env)
            mns_pub_response = mns_service.publish_notification(mns_notification_payload)

            if mns_pub_response["status_code"] != 200:
                raise RuntimeError("MNS publish failed")
            logger.info(
                "Successfully created MNS notification",
                trace_ids={
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
            batch_item_failures.append({"itemIdentifier": message_id})

    if batch_item_failures:
        logger.warning(f"Batch completed with {len(batch_item_failures)} failures")
    else:
        logger.info(f"Successfully processed all {len(event_records)} messages")

    return {"batchItemFailures": batch_item_failures}


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
