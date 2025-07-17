import os
import logging
from boto3 import client as boto3_client

logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")

REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")
s3_client = boto3_client("s3", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
