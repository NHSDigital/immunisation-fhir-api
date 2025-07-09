"""Initialise s3, kinesis, lambda and redis clients"""

from boto3 import client as boto3_client
import os
import logging
import redis

REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")

s3_client = boto3_client("s3", region_name=REGION_NAME)
kinesis_client = boto3_client("kinesis", region_name=REGION_NAME)
lambda_client = boto3_client("lambda", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
sqs_client = boto3_client("sqs", region_name=REGION_NAME)

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")

redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
