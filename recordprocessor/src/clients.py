"""Initialise s3 and kinesis clients"""

# import os
import logging
from boto3 import client as boto3_client, resource as boto3_resource
from botocore.config import Config
from redis_cacher import RedisCacher

REGION_NAME = "eu-west-2"

s3_client = boto3_client("s3", region_name=REGION_NAME)
kinesis_client = boto3_client(
    "kinesis", region_name=REGION_NAME, config=Config(retries={"max_attempts": 3, "mode": "standard"})
)
sqs_client = boto3_client("sqs", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)
lambda_client = boto3_client("lambda", region_name=REGION_NAME)

dynamodb_resource = boto3_resource("dynamodb", region_name=REGION_NAME)

# redis_client = RedisCacher(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"))
host = "immunisation-redis-cluster.0y9mwl.0001.euw2.cache.amazonaws.com"
redis_client = RedisCacher(host, 6379)
# Logger
logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")
