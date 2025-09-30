from redis_cacher import RedisCacher
from common.clients import logger
from common.s3_event import S3EventRecord
from common.service_return import ServiceReturn
'''
    Record Processor
    This module processes individual S3 records from an event.
    It is used to upload data to Redis ElastiCache.
'''


def process_record(record: S3EventRecord) -> ServiceReturn:
    try:
        logger.info("Processing S3 r bucket: %s, key: %s",
                    record.get_bucket_name(), record.get_object_key())
        bucket_name = record.get_bucket_name()
        file_key = record.get_object_key()

        base_log_data = {
            "file_key": file_key
        }

        try:
            service_result = RedisCacher.upload(bucket_name, file_key)
            if service_result.is_success:
                result = service_result.value
                result.update(base_log_data)
                return ServiceReturn(value=result)
            else:
                return ServiceReturn(
                    status=500,
                    message=f"Failed to upload to cache for filename '{file_key}': {service_result.message}")

        except Exception as error:  # pylint: disable=broad-except
            logger.exception("Error uploading to cache for filename '%s'", file_key)
            error_data = {"status": "error", "message": str(error)}
            error_data.update(base_log_data)
            return ServiceReturn(value=error_data)

    except Exception:  # pylint: disable=broad-except
        return ServiceReturn(value={"status": "error", "message": "Error processing record"})
