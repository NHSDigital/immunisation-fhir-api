import os
import redis
from common.clients import logger

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

redis_client = None


def get_redis_client():
    global redis_client
    if redis_client is None:
        print("SAW: get_redis_client")
        logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")
        redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    return redis_client
