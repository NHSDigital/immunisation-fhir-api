from clients import logger
from s3_event import S3EventRecord
from redis_cacher import RedisCacher
'''
    Record Processor
    This module processes individual S3 records from an event.
    It is used to upload data to Redis ElastiCache.
'''


def record_processor(record: S3EventRecord) -> bool:

    try:
        logger.info("Processing S3 event for bucket: %s, key: %s",
                    record.get_bucket_name(), record.get_object_key())
        bucket_name = record.get_bucket_name()
        file_key = record.get_object_key()

        try:

            return RedisCacher.upload(bucket_name, file_key)

        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error uploading to cache for file '%s': %s", file_key, error)
            return False

    except Exception:  # pylint: disable=broad-except
        logger.exception("Error obtaining file_key")
        return False
