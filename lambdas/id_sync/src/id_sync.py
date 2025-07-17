from common.clients import logger
from clients import STREAM_NAME
from common.log_decorator import logging_decorator
from record_processor import process_record

'''
    Event Processor
    The Business Logic for the Redis Sync Lambda Function.
    This module processes S3 events and iterates through each record to process them individually.'''


@logging_decorator(prefix="id_sync", stream_name=STREAM_NAME)
def handler(event, _):

    try:
        if "Records" in event:
            logger.info("Processing S3 event with %d records", len(event.get('Records', [])))
            record_count = len(event.get('Records', []))
            if record_count == 0:
                logger.info("No records found in event")
                return {"status": "success", "message": "No records found in event"}
            else:
                error_count = 0
                file_keys = []
                for record in event.get('Records', []):
                    record_result = process_record(record, None)
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
