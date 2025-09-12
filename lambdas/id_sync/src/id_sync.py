from typing import Any, Dict

from common.clients import logger, STREAM_NAME
from common.log_decorator import logging_decorator
from common.aws_lambda_event import AwsLambdaEvent
from exceptions.id_sync_exception import IdSyncException
from record_processor import process_record

"""
- Parses the incoming AWS event into `AwsLambdaEvent` and iterate its `records`.
- Delegate each record to `process_record` and collect `nhs_number` from each result.
- If any record has status == "error" raise `IdSyncException` with aggregated nhs_numbers.
- Any unexpected error is wrapped into `IdSyncException(message="Error processing id_sync event")`.
"""


@logging_decorator(prefix="id_sync", stream_name=STREAM_NAME)
def handler(event_data: Dict[str, Any], _context) -> Dict[str, Any]:
    try:
        logger.info("id_sync handler invoked")
        event = AwsLambdaEvent(event_data)
        records = event.records

        if not records:
            return {"status": "success", "message": "No records found in event"}

        logger.info("id_sync processing event with %d records", len(records))

        # Process records in order. Let any unexpected exception bubble to the outer handler
        # so tests that expect a wrapped IdSyncException keep working.
        results = [process_record(record) for record in records]
        nhs_numbers = [result["nhs_number"] for result in results]
        error_count = sum(1 for result in results if result.get("status") == "error")

        if error_count:
            raise IdSyncException(message=f"Processed {len(records)} records with {error_count} errors",
                                  nhs_numbers=nhs_numbers)

        response = {"status": "success",
                    "message": f"Successfully processed {len(records)} records",
                    "nhs_numbers": nhs_numbers}

        logger.info("id_sync handler completed: %s", response)
        return response

    except IdSyncException as e:
        # Preserve domain exceptions but ensure they're logged
        logger.exception(f"id_sync error: {e.message}")
        raise
    except Exception:
        msg = "Error processing id_sync event"
        logger.exception(msg)
        # Raise a domain exception with a predictable message for callers/tests
        raise IdSyncException(message=msg)
