"""Initialise clients and logger"""

import logging
from boto3 import client as boto3_client, resource as boto3_resource

REGION_NAME = "eu-west-2"

firehose_client = boto3_client("firehose", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)

dynamodb_resource = boto3_resource("dynamodb", region_name=REGION_NAME)

s3_client = None
def get_s3_client():
    global s3_client
    if s3_client is None:
        s3_client = boto3_client("s3", region_name=REGION_NAME)
    return s3_client

# Logger
logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")
