from clients import logger
from event_processor import event_processor

'''Redis Sync Lambda Handler
    This contains the handler code and nothing else.
    It is used to process S3 events and upload data to Redis.
    It is triggered by S3 events and processes the event to upload data to Redis.
'''


def handler(event, context):

    logger.info("Sync Handler")
    try:

        return event_processor(event, context)

    except Exception:  # pylint: disable=broad-except
        logger.exception("Error in Redis Sync Processor")
        return False
