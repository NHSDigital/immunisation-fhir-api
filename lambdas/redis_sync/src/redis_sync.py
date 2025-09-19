from event_read import read_event
from record_processor import process_record
from common.clients import get_redis_client, STREAM_NAME, logger
from common.log_decorator import logging_decorator
from common.s3_event import S3Event
'''
    Event Processor
    The Business Logic for the Redis Sync Lambda Function.
    This module processes S3 events and iterates through each record to process them individually.'''


def _process_all_records(s3_records: list) -> dict:
    record_count = len(s3_records)
    error_count = 0
    file_keys = []
    for record in s3_records:
        record_result = process_record(record)
        file_keys.append(record_result["file_key"])
        if record_result["status"] == "error":
            error_count += 1
    if error_count > 0:
        logger.error("Processed %d records with %d errors", record_count, error_count)
        return {"status": "error", "message": f"Processed {record_count} records with {error_count} errors",
                "file_keys": file_keys}
    else:
        logger.info("Successfully processed all %d records", record_count)
        return {"status": "success", "message": f"Successfully processed {record_count} records",
                "file_keys": file_keys}


@logging_decorator(prefix="redis_sync", stream_name=STREAM_NAME)
def handler(event, _):

    try:
        no_records = "No records found in event"
        # check if the event requires a read, ie {"read": "my-hashmap"}
        if "read" in event:
            return read_event(get_redis_client(), event, logger)
        elif "Records" in event:
            logger.info("Processing S3 event with %d records", len(event.get('Records', [])))
            s3_records = S3Event(event).get_s3_records()
            if not s3_records:
                logger.info(no_records)
                return {"status": "success", "message": no_records}
            else:
                return _process_all_records(s3_records)
        else:
            logger.info(no_records)
            return {"status": "success", "message": no_records}

    except Exception:
        logger.exception("Error processing S3 event")
        return {"status": "error", "message": "Error processing S3 event"}
