import os

import redis

from common.clients import logger

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

redis_client = redis.StrictRedis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), decode_responses=True)

# for lambdas which require a global redis_client
global_redis_client = None


def get_redis_client():
    global global_redis_client
    if global_redis_client is None:
        logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")
        global_redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    return global_redis_client
