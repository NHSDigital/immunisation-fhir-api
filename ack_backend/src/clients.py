"""Initialise clients and logger"""

import logging
from boto3 import client as boto3_client

REGION_NAME = "eu-west-2"

firehose_client = boto3_client("firehose", region_name=REGION_NAME)


# Logger
logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")
