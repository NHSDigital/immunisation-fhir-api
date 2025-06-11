import os
import logging
from redis_cacher import RedisCacher

# Logger
logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")

# TODO Remove defaults for production
REDIS_HOST = os.getenv("REDIS_HOST", "immunisation-redis-cluster.0y9mwl.0001.euw2.cache.amazonaws.com")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

redis_cacher = RedisCacher(REDIS_HOST, REDIS_PORT, logger)

# disease_vaccine_mapping = DiseaseMapping(redis_cacher)
