import logging
import os

from boto3 import client as boto3_client
from boto3 import resource as boto3_resource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", "firehose-name-not-defined")
CONFIG_BUCKET_NAME = os.getenv("CONFIG_BUCKET_NAME", "variconfig-bucketable-not-defined")

REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")

s3_client = boto3_client("s3", region_name=REGION_NAME)

# for lambdas which require a global s3_client
global_s3_client = None


def get_s3_client():
    global global_s3_client
    if global_s3_client is None:
        global_s3_client = boto3_client("s3", region_name=REGION_NAME)
    return global_s3_client


firehose_client = boto3_client("firehose", region_name=REGION_NAME)
secrets_manager_client = boto3_client("secretsmanager", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)
dynamodb_resource = boto3_resource("dynamodb", region_name=REGION_NAME)
