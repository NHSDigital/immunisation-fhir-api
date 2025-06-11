"Upload the content from a config file in S3 to ElastiCache (Redis)"

import json
import redis


class RedisCacher():
    """ RedisCacher abstraction class to decouple application code
    from direct use of Redis client.
    Also centralised error handling & extensibility.
    """

    def __init__(self, redis_host, redis_port, logger):
        try:
            self.logger = logger
            # Attempt to connect to Redis
            self.redis_client = redis.StrictRedis(redis_host, redis_port, decode_responses=True)
            # Check the connection with a PING command
            if self.redis_client.ping():
                logger.info("Successfully connected to Redis.")
            else:
                logger.error("Failed to connect to Redis.")
        except Exception as e:
            logger.exception(f"Connection to Redis failed: {e}")

    def get(self, key: str) -> dict:
        """Gets the value from Redis cache for the given key."""
        value = self.redis_client.get(key)
        if value is not None:
            return json.loads(value)
        return {}

    # save data to Redis cache
    def set(self, key: str, value: dict):
        """Sets the value in Redis cache for the given key."""
        try:
            self.redis_client.set(key, json.dumps(value))
        except Exception as e:
            raise RuntimeError(f"Failed to set key {key} in Redis: {e}")

    # def close(self):
    #     """Closes the Redis connection."""
    #     try:
    #         self.redis_client.close()
    #         self.redis_client.connection_pool.disconnect()
    #     except Exception as e:
    #         raise RuntimeError(f"Failed to close Redis connection: {e}")
    #     self.logger.info("Redis connection closed.")
