"Upload the content from a config file in S3 to ElastiCache (Redis)"

import json
from transform_map import transform_map
from common.clients import logger
from common.redis_client import get_redis_client
from common.s3_reader import S3Reader


class RedisCacher:
    """Class to handle interactions with ElastiCache (Redis) for configuration files."""

    @staticmethod
    def upload(bucket_name: str, file_key: str) -> dict:
        try:
            logger.info("Upload from s3 to Redis cache. file '%s'. bucket '%s'", file_key, bucket_name)

            # get from s3
            config_file_content = S3Reader.read(bucket_name, file_key)
            print(f"SAW: S3 file content for '{file_key}': {config_file_content}")
            if isinstance(config_file_content, str):
                config_file_content = json.loads(config_file_content)

            logger.info("Config file content for '%s': %s", file_key, config_file_content)

            # Transform
            print(f"SAW: Transforming file content for '{file_key}'")
            redis_mappings = transform_map(config_file_content, file_key)

            redis_client = get_redis_client()
            print(f"SAW: Redis mappings for '{file_key}': {redis_mappings}")
            for key, mapping in redis_mappings.items():
                print(f"SAW: Processing Redis key '{key}' with mapping: {mapping}")
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

            return {"status": "success", "message": f"File {file_key} uploaded to Redis cache."}
        except Exception:
            msg = f"Error uploading file '{file_key}' to Redis cache"
            logger.exception(msg)
            return {"status": "error", "message": msg}
