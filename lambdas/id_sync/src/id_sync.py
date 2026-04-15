"""
- Parses the incoming AWS event into `AwsLambdaEvent` and iterates its `records`.
- Delegates each record to `process_record` with per-record exception isolation.
- Returns {"batchItemFailures": [...]} for any failed records so SQS only re-drives the failing messages.
- A handler-level exception (bad event schema etc.) re-raises to trigger full batch retry.
"""

from typing import Any

from common.aws_lambda_event import AwsLambdaEvent
from common.clients import STREAM_NAME, logger
from common.log_decorator import logging_decorator
from record_processor import process_record


@logging_decorator(prefix="id_sync", stream_name=STREAM_NAME)
def handler(event_data: dict[str, Any], _context) -> dict[str, Any]:
    try:
        event = AwsLambdaEvent(event_data)
        records = event.records

        if not records:
            return {"status": "success", "message": "No records found in event"}

        logger.info("id_sync processing event with %d records", len(records))

        batch_item_failures = []

        for record in records:
            try:
                result = process_record(record)
                if result.get("status") == "error":
                    message_id = record.get("messageId")
                    logger.error(
                        "id_sync record processing failed for messageId: %s — %s",
                        message_id,
                        result.get("message"),
                    )
                    batch_item_failures.append({"itemIdentifier": message_id})
            except Exception:
                message_id = record.get("messageId")
                logger.exception("Unexpected error processing messageId: %s", message_id)
                batch_item_failures.append({"itemIdentifier": message_id})

        if batch_item_failures:
            logger.error("id_sync completed with %d/%d failures", len(batch_item_failures), len(records))
            return {"batchItemFailures": batch_item_failures}

        response = {"status": "success", "message": f"Successfully processed {len(records)} records"}
        logger.info("id_sync handler completed: %s", response)
        return response

    except Exception:
        logger.exception("Unexpected error processing id_sync event")
        raise
