"Upload the content from a config file in S3 to ElastiCache (Redis)"

import json
from clients import redis_client
from clients import logger
from transform_map import transform_map
from constants import RedisCacheKey
from s3_reader import S3Reader


class RedisCacher:
    """Class to handle interactions with ElastiCache (Redis) for configuration files."""

    @staticmethod
    def upload(bucket_name: str, file_key: str) -> dict:

        try:
            logger.info("Upload from s3 to Redis cache. file '%s'. bucket '%s'", file_key, bucket_name)

            # get from s3
            config_file_content = S3Reader.read(bucket_name, file_key)
            if isinstance(config_file_content, str):
                config_file_content = json.loads(config_file_content)

            logger.info("Config file content for '%s': %s", file_key, config_file_content)

            # Transform
            redis_mappings = transform_map(config_file_content, file_key)

            for key, mapping in redis_mappings.items():
                safe_mapping = {k: json.dumps(v) if isinstance(v, list) else v for k, v in mapping.items()}
                redis_client.hmset(key, safe_mapping)

            return {"status": "success", "message": f"File {file_key} uploaded to Redis cache."}
        except Exception:
            msg = f"Error uploading file '{file_key}' to Redis cache"
            logger.exception(msg)
            return {"status": "error", "message": msg}

    @staticmethod
    def get_cached_config_json(file_type) -> dict:
        """Gets and returns the permissions config file content from ElastiCache (Redis)."""
        return json.loads(redis_client.get(file_type))

    @staticmethod
    def get_cached_permissions_config_json() -> dict:
        """ return Permissions config data from cache."""
        return RedisCacher.get_cached_config_json(RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY)

    @staticmethod
    def get_cached_disease_mapping_json() -> dict:
        """return Disease mapping data from cache."""
        return RedisCacher.get_cached_config_json(RedisCacheKey.DISEASE_MAPPING_FILE_KEY)
