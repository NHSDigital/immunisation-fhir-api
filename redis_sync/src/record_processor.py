from clients import logger
from s3_event import S3EventRecord
from redis_cacher import RedisCacher
# from logging_decorator import logging_decorator
'''
    Record Processor
    This module processes individual S3 records from an event.
    It is used to upload data to Redis ElastiCache.
'''


# NOTE: logging_decorator is applied to handle_record function, rather than lambda_handler, because
# the logging_decorator is for an individual record, whereas the lambda_handler could potentially be handling
# multiple records.
def record_processor(record: S3EventRecord) -> bool:

    try:
        logger.info("Processing S3 r bucket: %s, key: %s",
                    record.get_bucket_name(), record.get_object_key())
        bucket_name = record.get_bucket_name()
        file_key = record.get_object_key()

        try:

            return RedisCacher.upload(bucket_name, file_key)

        except Exception as error:  # pylint: disable=broad-except
            logger.exception("Error uploading to cache for filename '%s'", file_key)
            return {"status": "error", "message": str(error)}

    except Exception:  # pylint: disable=broad-except
        logger.exception("Error obtaining file_key")
        return {"status": "error", "message": "Error obtaining file_key"}
