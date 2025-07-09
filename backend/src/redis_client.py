import logging
import os

import redis


REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")

redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
