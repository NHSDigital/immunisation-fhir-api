"""Initialise s3 and kinesis clients"""

import logging
import os

import redis
from boto3 import client as boto3_client, resource as boto3_resource
from botocore.config import Config

REGION_NAME = "eu-west-2"
REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

s3_client = boto3_client("s3", region_name=REGION_NAME)
kinesis_client = boto3_client(
    "kinesis", region_name=REGION_NAME, config=Config(retries={"max_attempts": 3, "mode": "standard"})
)
sqs_client = boto3_client("sqs", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)
lambda_client = boto3_client("lambda", region_name=REGION_NAME)
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

dynamodb_resource = boto3_resource("dynamodb", region_name=REGION_NAME)

# Logger
logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")
