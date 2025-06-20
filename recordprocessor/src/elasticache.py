import json
from constants import RedisCacheKeys
from clients import redis_client


def get_disease_mapping_json_from_cache() -> dict:
    """Gets and returns the disease mapping file content from ElastiCache (Redis)."""
    return json.loads(redis_client.get(RedisCacheKeys.DISEASE_MAPPING_FILE_KEY))
