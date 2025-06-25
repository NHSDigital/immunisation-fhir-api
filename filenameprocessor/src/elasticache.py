"Upload the content from a config file in S3 to ElastiCache (Redis)"

import json
from clients import s3_client, redis_client
from constants import PERMISSIONS_CONFIG_FILE_KEY, VACCINE_TYPE_TO_DISEASES_HASH_KEY


def upload_to_elasticache(file_key: str, bucket_name: str) -> None:
    """Uploads the config file content from S3 to ElastiCache (Redis)."""
    config_file = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    config_file_content = config_file["Body"].read().decode("utf-8")
    # Use the file_key as the Redis key and file content as the value
    redis_client.set(file_key, config_file_content)


def get_permissions_config_json_from_cache() -> dict:
    """Gets and returns the permissions config file content from ElastiCache (Redis)."""
    return json.loads(redis_client.get(PERMISSIONS_CONFIG_FILE_KEY))


def get_valid_vaccine_types_from_cache() -> list[str]:
    return redis_client.hkeys(VACCINE_TYPE_TO_DISEASES_HASH_KEY)
