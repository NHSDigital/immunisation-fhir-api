"Upload the content from a config file in S3 to ElastiCache (Redis)"

import json
import redis
from clients import redis_client
from constants import DISEASE_MAPPING_FILE_KEY


class RedisCache():
    def __init__(self, redis_host, redis_port):
        self.redis_client = redis.StrictRedis(redis_host, redis_port, decode_responses=True)


def get_disease_mapping_json_from_cache() -> dict:
    """Gets and returns the disease mapping file from ElastiCache (Redis)."""

    return json.loads(redis_client.get(DISEASE_MAPPING_FILE_KEY))
