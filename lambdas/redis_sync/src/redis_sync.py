from clients import logger
from s3_event import S3Event
from record_processor import process_record
from event_read import read_event
from log_decorator import logging_decorator
from clients import redis_client
'''
    Event Processor
    The Business Logic for the Redis Sync Lambda Function.
    This module processes S3 events and iterates through each record to process them individually.'''


@logging_decorator(prefix="redis_sync")
def handler(event, _):

    try:
        # check if the event requires a read, ie {"read": "my-hashmap"}
        if "read" in event:
            return read_event(redis_client, event, logger)
        elif "Records" in event:
            logger.info("Processing S3 event with %d records", len(event.get('Records', [])))
            s3_event = S3Event(event)
            record_count = len(s3_event.get_s3_records())
            if record_count == 0:
                logger.info("No records found in event")
                return {"status": "success", "message": "No records found in event"}
            else:
                error_count = 0
                file_keys = []
                for record in s3_event.get_s3_records():
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
        else:
            logger.info("No records found in event")
            return {"status": "success", "message": "No records found in event"}

    except Exception:
        logger.exception("Error processing S3 event")
        return {"status": "error", "message": "Error processing S3 event"}
