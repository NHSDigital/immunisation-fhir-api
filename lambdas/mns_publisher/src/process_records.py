import json
import os

from aws_lambda_typing.events.sqs import SQSMessage

from common.api_clients.mns_service import MnsService
from common.api_clients.mns_setup import get_mns_service
from common.api_clients.mock_mns_service import MockMnsService
from common.clients import logger
from create_notification import create_mns_notification

mns_env = os.getenv("MNS_ENV", "int")
_mns_service: MnsService | MockMnsService | None = None


def _get_runtime_mns_service() -> MnsService | MockMnsService:
    global _mns_service
    if _mns_service is None:
        _mns_service = get_mns_service(mns_env=mns_env)

    return _mns_service


def process_records(records: list[SQSMessage]) -> dict[str, list]:
    """
    Process multiple SQS records.
    Args: records: List of SQS records to process
    Returns: List of failed item identifiers for partial batch failure
    """
    batch_item_failures = []
    mns_service = _get_runtime_mns_service()

    for record in records:
        try:
            process_record(record, mns_service)
        except Exception:
            message_id = record.get("messageId", "unknown")
            batch_item_failures.append({"itemIdentifier": message_id})
            logger.exception("Failed to process record", extra={"message_id": message_id})

    if batch_item_failures:
        logger.warning(f"Batch completed with {len(batch_item_failures)} failures")
    else:
        logger.info(f"Successfully processed all {len(records)} messages")

    return {"batchItemFailures": batch_item_failures}


def process_record(record: SQSMessage, mns_service: MnsService | MockMnsService) -> None:
    """
    Process a single SQS record.
    Args:
        record: SQS record containing DynamoDB stream data
        mns_service: MNS service instance for publishing
    Returns: Failure dict with itemIdentifier if processing failed, None if successful
    """
    message_id, immunisation_id = extract_trace_ids(record)
    notification_id = None

    mns_notification_payload = create_mns_notification(record)
    notification_id = mns_notification_payload.get("id")

    action_flag = mns_notification_payload.get("filtering", {}).get("action")
    logger.info(
        "Processing message",
        extra={
            "notification_id": notification_id,
            "message_id": message_id,
            "immunisation_id": immunisation_id,
            "action_flag": action_flag,
        },
    )

    mns_service.publish_notification(mns_notification_payload)
    logger.info("Successfully created MNS notification", extra={"mns_notification_id": notification_id})


def extract_trace_ids(record: SQSMessage) -> tuple[str, str | None]:
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
