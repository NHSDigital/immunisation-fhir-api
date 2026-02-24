from aws_lambda_typing import context, events

from common.clients import logger
from process_records import process_records


def lambda_handler(event: events.SQSEvent, _: context.Context) -> dict[str, list]:
    event_records = event.get("Records", [])
    batch_item_failures = process_records(event_records)

    if batch_item_failures:
        logger.warning(f"Batch completed with {len(batch_item_failures)} failures")
    else:
        logger.info(f"Successfully processed all {len(event_records)} messages")

    return {"batchItemFailures": batch_item_failures}
