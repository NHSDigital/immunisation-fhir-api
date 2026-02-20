"""
- Parses the incoming AWS event into `AwsLambdaEvent` and iterate its `records`.
- Delegate each record to `process_record` and collect `nhs_number` from each result.
- If any record has status == "error" raise `PdsSyncException` with aggregated nhs_numbers.
- Any unexpected error is wrapped into `PdsSyncException(message="Error processing id_sync event")`.
"""

from typing import Any, Dict

from common.api_clients.errors import PdsSyncException
from common.aws_lambda_event import AwsLambdaEvent
from common.clients import STREAM_NAME, logger
from common.log_decorator import logging_decorator
from record_processor import process_record


@logging_decorator(prefix="id_sync", stream_name=STREAM_NAME)
def handler(event_data: Dict[str, Any], _context) -> Dict[str, Any]:
    try:
        event = AwsLambdaEvent(event_data)
        records = event.records

        if not records:
            return {"status": "success", "message": "No records found in event"}

        logger.info("id_sync processing event with %d records", len(records))

        error_count = 0

        for record in records:
            result = process_record(record)

            if result.get("status") == "error":
                error_count += 1

        if error_count > 0:
            raise PdsSyncException(
                message=f"Processed {len(records)} records with {error_count} errors",
            )

        response = {"status": "success", "message": f"Successfully processed {len(records)} records"}

        logger.info("id_sync handler completed: %s", response)
        return response

    except PdsSyncException as e:
        logger.exception(f"id_sync error: {e.message}")
        raise
    except Exception:
        msg = "Error processing id_sync event"
        logger.exception(msg)
        raise PdsSyncException(message=msg)
