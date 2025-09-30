from event_read import read_event
from record_processor import process_record
from common.clients import STREAM_NAME, logger
from common.log_decorator import logging_decorator
from common.redis_client import get_redis_client
from common.s3_event import S3Event
from common.service_return import ServiceReturn
'''
    Event Processor
    The Business Logic for the Redis Sync Lambda Function.
    This module processes S3 events and iterates through each record to process them individually.'''


def _process_all_records(s3_records: list) -> dict:
    record_count = len(s3_records)
    error_count = 0
    file_keys = []
    for record in s3_records:
        service_result = process_record(record)
        file_keys.append(service_result.value.get("file_key"))
        if service_result.status == 500:
            error_count += 1
    if error_count > 0:
        logger.error("Processed %d records with %d errors", record_count, error_count)
        return ServiceReturn(value={"status": "error",
                                    "message": f"Processed {record_count} records with {error_count} errors",
                                    "file_keys": file_keys})
    else:
        logger.info("Successfully processed all %d records", record_count)
        return ServiceReturn(
            value={"status": "success",
                   "message": f"Successfully processed {record_count} records",
                   "file_keys": file_keys})


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
                service_result = _process_all_records(s3_records)
                if service_result.is_success:
                    return service_result.value
                else:
                    return {"status": "error", "message": service_result.value.get("message"),
                            "file_keys": service_result.value.get("file_keys", [])}
        else:
            logger.info(no_records)
            return {"status": "success", "message": no_records}

    except Exception:
        logger.exception("Error processing S3 event")
        return {"status": "error", "message": "Error processing S3 event"}
