"Upload the content from a config file in S3 to ElastiCache (Redis)"

import json
from transform_map import transform_map
from common.clients import logger
from common.redis_client import get_redis_client
from common.s3_reader import S3Reader
from common.service_return import ServiceReturn


class RedisCacher:
    """Class to handle interactions with ElastiCache (Redis) for configuration files."""

    @staticmethod
    def upload(bucket_name: str, file_key: str) -> ServiceReturn:
        try:
            logger.info("Upload from s3 to Redis cache. file '%s'. bucket '%s'", file_key, bucket_name)

            # get from s3
            result = S3Reader.read(bucket_name, file_key)
            if result.is_success:
                config_file_content = result.value
                if isinstance(config_file_content, str):
                    config_file_content = json.loads(config_file_content)

                logger.info("Config file content for '%s': %s", file_key, config_file_content)
            else:
                logger.error("Failed to read S3 file '%s': %s", file_key, result.message)
                return ServiceReturn(status=500, message=result.message)

            # Transform
            redis_mappings = transform_map(config_file_content, file_key)

            redis_client = get_redis_client()
            for key, mapping in redis_mappings.items():
                safe_mapping = {
                    k: json.dumps(v) if isinstance(v, list) else v
                    for k, v in mapping.items()
                }
                existing_mapping = redis_client.hgetall(key)
                logger.info("Existing mapping for %s: %s", key, existing_mapping)
                redis_client.hmset(key, safe_mapping)
                logger.info("New mapping for %s: %s", key, safe_mapping)
                fields_to_delete = [k for k in existing_mapping if k not in safe_mapping]
                if fields_to_delete:
                    redis_client.hdel(key, *fields_to_delete)
                    logger.info("Deleted mapping fields for %s: %s", key, fields_to_delete)

            return ServiceReturn(value={"status": "success", "message": f"File {file_key} uploaded to Redis cache."})
        except Exception:
            msg = f"Error uploading file '{file_key}' to Redis cache"
            logger.exception(msg)
            return ServiceReturn(status=500, message=msg)
