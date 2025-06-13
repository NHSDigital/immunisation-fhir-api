"""Initialise clients, resources and logger. Note that all clients, resources and logger for the E2E BATCH
should be initialised ONCE ONLY (in this file) and then imported into the files where they are needed.
"""

import logging
from constants import (environment, REGION)
from boto3 import client as boto3_client, resource as boto3_resource


# AWS Clients and Resources


s3_client = boto3_client("s3", region_name=REGION)

dynamodb = boto3_resource("dynamodb", region_name=REGION)
table_name = f"imms-{environment}-imms-events"
table = dynamodb.Table(table_name)
# Logger
logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")
