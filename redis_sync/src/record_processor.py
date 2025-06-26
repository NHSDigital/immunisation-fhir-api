from clients import logger
from s3_event import S3EventRecord
from redis_cacher import RedisCacher
'''
    Record Processor
    This module processes individual S3 records from an event.
    It is used to upload data to Redis ElastiCache.
'''


def process_record(record: S3EventRecord) -> dict:
    try:
        logger.info("Processing S3 r bucket: %s, key: %s",
                    record.get_bucket_name(), record.get_object_key())
        bucket_name = record.get_bucket_name()
        file_key = record.get_object_key()

        base_log_data = {
            "file_key": file_key
        }

        try:
            result = RedisCacher.upload(bucket_name, file_key)
            result.update(base_log_data)
            return result

        except Exception as error:  # pylint: disable=broad-except
            logger.exception("Error uploading to cache for filename '%s'", file_key)
            error_data = {"status": "error", "message": str(error)}
            error_data.update(base_log_data)
            return error_data

    except Exception:  # pylint: disable=broad-except
        msg = "Error processing record"
        logger.exception(msg)
        return {"status": "error", "message": msg}
