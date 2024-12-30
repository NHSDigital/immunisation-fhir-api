"""Initialise s3 and kinesis clients"""

import logging
from boto3 import client as boto3_client

REGION_NAME = "eu-west-2"

s3_client = boto3_client("s3", region_name=REGION_NAME)
kinesis_client = boto3_client("kinesis", region_name=REGION_NAME)

logging.basicConfig(level="INFO")
logger = logging.getLogger()
