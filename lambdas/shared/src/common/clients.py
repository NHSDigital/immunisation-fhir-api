import os
import logging
from boto3 import client as boto3_client, resource as boto3_resource

logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Root logger level

if logger.hasHandlers():
    logger.handlers.clear()

console = logging.StreamHandler()
console.setLevel(logging.INFO)  # Handler must also allow INFO logs

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)

logger.addHandler(console)

STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", "firehose-name-not-defined")
CONFIG_BUCKET_NAME = os.getenv("CONFIG_BUCKET_NAME", "variconfig-bucketable-not-defined")

REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")

s3_client = boto3_client("s3", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)

secrets_manager_client = boto3_client("secretsmanager", region_name=REGION_NAME)
dynamodb_resource = boto3_resource("dynamodb", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)
