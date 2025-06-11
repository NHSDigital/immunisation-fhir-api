import os
import logging
import redis
# from redis_cacher import RedisCacher
from boto3 import client as boto3_client

# Logger
logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")

CONFIG_BUCKET_NAME = os.getenv("CONFIG_BUCKET_NAME", "variable-not-defined")
REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")
REDIS_HOST = os.getenv("REDIS_HOST", "immunisation-redis-cluster.0y9mwl.0001.euw2.cache.amazonaws.com")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

s3_client = boto3_client("s3", region_name=REGION_NAME)
logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# logger.info("Creating RedisCacher instance.")
# redis_cacher = RedisCacher(REDIS_HOST, REDIS_PORT, logger)

# disease_vaccine_mapping = DiseaseMapping(redis_cacher)
