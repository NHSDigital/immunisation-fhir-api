"""Initialise clients, resources and logger. Note that all clients, resources and logger for the E2E BATCH
should be initialised ONCE ONLY (in this file) and then imported into the files where they are needed.
"""

import logging
from boto3 import client as boto3_client

# AWS Clients and Resources
REGION = "eu-west-2"

s3_client = boto3_client("s3", region_name=REGION)

# Logger
logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")
