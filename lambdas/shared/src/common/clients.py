import os
import logging
from boto3 import client as boto3_client, resource as boto3_resource

# Configure root logger with a numeric level and ensure any handlers accept INFO.
logging.basicConfig(level=logging.INFO)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for handler in root_logger.handlers:
	# make sure handler level is not higher than INFO
	try:
		handler.setLevel(logging.INFO)
	except Exception:
		pass

# Export the configured root logger for modules to use
logger = root_logger

STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", "firehose-name-not-defined")
CONFIG_BUCKET_NAME = os.getenv("CONFIG_BUCKET_NAME", "variconfig-bucketable-not-defined")

REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")

s3_client = boto3_client("s3", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)

secrets_manager_client = boto3_client("secretsmanager", region_name=REGION_NAME)
dynamodb_resource = boto3_resource("dynamodb", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)
