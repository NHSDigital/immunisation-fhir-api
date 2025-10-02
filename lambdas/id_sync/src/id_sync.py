"""
- Parses the incoming AWS event into `AwsLambdaEvent` and iterate its `records`.
- Delegate each record to `process_record` and collect `nhs_number` from each result.
- If any record has status == "error" raise `IdSyncException` with aggregated nhs_numbers.
- Any unexpected error is wrapped into `IdSyncException(message="Error processing id_sync event")`.
"""

from typing import Any, Dict
from common.aws_lambda_event import AwsLambdaEvent
from common.clients import logger, STREAM_NAME
from common.log_decorator import logging_decorator
from exceptions.id_sync_exception import IdSyncException
from record_processor import process_record


@logging_decorator(prefix="id_sync", stream_name=STREAM_NAME)
def handler(event_data: Dict[str, Any], _context) -> Dict[str, Any]:
    try:
        event = AwsLambdaEvent(event_data)
        records = event.records

        if not records:
            return {"status": "success", "message": "No records found in event"}

        logger.info("id_sync processing event with %d records", len(records))

        results = []
        nhs_numbers = []
        error_count = 0

        for record in records:
            result = process_record(record)
            results.append(result)

            if "nhs_number" in result:
                nhs_numbers.append(result["nhs_number"])

            if result.get("status") == "error":
                error_count += 1

        if error_count > 0:
            raise IdSyncException(message=f"Processed {len(records)} records with {error_count} errors",
                                  nhs_numbers=nhs_numbers)

        response = {
            "status": "success",
            "message": f"Successfully processed {len(records)} records",
            "nhs_numbers": nhs_numbers
            }

        logger.info("id_sync handler completed: %s", response)
        return response

    except IdSyncException as e:
        logger.exception(f"id_sync error: {e.message}")
        raise
    except Exception:
        msg = "Error processing id_sync event"
        logger.exception(msg)
        raise IdSyncException(message=msg)
