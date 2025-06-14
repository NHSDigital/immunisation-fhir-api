"Upload the content from a config file in S3 to ElastiCache (Redis)"

import json
from clients import redis_client
from transform_map import transform_map
from constants import RedisCacheKey
from s3_reader import S3Reader


class RedisCacher:
    """Class to handle interactions with ElastiCache (Redis) for configuration files."""

    @staticmethod
    def upload(bucket_name: str, file_key: str) -> None:

        config_file_content = S3Reader.read(bucket_name, file_key)

        # Transform the content based on the file type
        trx_data = transform_map(config_file_content, file_key)

        # Use the file_key as the Redis key and file content as the value
        redis_client.set(file_key, trx_data)
        return True

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
