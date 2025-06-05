"Upload the content from a config file in S3 to ElastiCache (Redis)"
import json
import redis
from clients import logger


class RedisCacher():
    def __init__(cls, redis_host, redis_port):
        try:
            # Attempt to connect to Redis
            cls.redis_client = redis.StrictRedis(redis_host, redis_port, decode_responses=True)
            # Check the connection with a PING command
            if cls.redis_client.ping():
                logger.info("Successfully connected to Redis.")
            else:
                logger.error("Failed to connect to Redis.")
        except Exception as e:
            logger.exception(f"Connection to Redis failed: {e}")

    def get_cache(cls, key: str) -> dict:
        """Gets the value from Redis cache for the given key."""
        value = cls.redis_client.get(key)
        if value is not None:
            return json.loads(value)
        return {}
