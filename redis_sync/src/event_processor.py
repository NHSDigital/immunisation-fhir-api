from clients import logger
from s3_event import S3Event
from record_processor import record_processor
from event_read import read_event
from clients import redis_client
'''
    Event Processor
    The Business Logic for the Redis Sync Lambda Function.
    This module processes S3 events and iterates through each record to process them individually.'''


def event_processor(event, context):

    try:
        # check if the event requires a read, ie {"read": "my-hashmap"}
        if "read" in event:
            return read_event(redis_client, event, logger)
        elif "Records" in event:
            logger.info("Processing S3 event with %d records", len(event.get('Records', [])))
            s3Event = S3Event(event)
            record_count = len(s3Event.get_s3_records())
            error_count = 0
            for record in s3Event.get_s3_records():
                record_result = record_processor(record)
                if record_result["status"] == "error":
                    error_count += 1
            if error_count > 0:
                logger.error("Processed %d records with %d errors", record_count, error_count)
                return {"status": "error", "message": f"Processed {record_count} records with {error_count} errors"}
            else:
                logger.info("Successfully processed all %d records", record_count)
                return {"status": "success", "message": f"Successfully processed {record_count} records"}
        else:
            logger.info("No records found in event")
            return {"status": "success", "message": "No records found in event"}

    except Exception:
        logger.exception("Error processing S3 event")
        return {"status": "error", "message": "Error processing S3 event"}
