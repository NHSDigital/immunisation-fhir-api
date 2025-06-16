from clients import logger
from s3_event import S3Event
from record_processor import record_processor
'''
    Event Processor
    The Business Logic for the Redis Sync Lambda Function.
    This module processes S3 events and iterates through each record to process them individually.'''


def event_processor(event, context):

    try:

        logger.info("Processing S3 event with %d records", len(event.get('Records', [])))
        s3Event = S3Event(event)
        for record in s3Event.get_s3_records():
            record_processor(record)
        return True

    except Exception:
        logger.exception("Error processing S3 event")
        return False
