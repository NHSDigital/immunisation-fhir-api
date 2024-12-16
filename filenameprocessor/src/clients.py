"""Initialise clients, resources and logger. Note that all clients, resources and logger for the filenameprocessor
lambda should be initialised ONCE ONLY (in this file) and then imported into the files where they are needed."""

import os
import logging
import redis
from boto3 import client as boto3_client, resource as boto3_resource

# AWS Clients and Resources
REGION_NAME = "eu-west-2"

s3_client = boto3_client("s3", region_name=REGION_NAME)
sqs_client = boto3_client("sqs", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)

dynamodb_resource = boto3_resource("dynamodb", region_name=REGION_NAME)

# Redis Client
redis_client = redis.StrictRedis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), decode_responses=True)

# Logger
logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")
