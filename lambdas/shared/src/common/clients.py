import os
import logging
import redis
from boto3 import client as boto3_client, resource as boto3_resource

logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")

STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", "firehose-name-not-defined")
CONFIG_BUCKET_NAME = os.getenv("CONFIG_BUCKET_NAME", "variconfig-bucketable-not-defined")

REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

s3_client = boto3_client("s3", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)

secrets_manager_client = boto3_client("secretsmanager", region_name=REGION_NAME)
dynamodb_resource = boto3_resource("dynamodb", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)

logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
