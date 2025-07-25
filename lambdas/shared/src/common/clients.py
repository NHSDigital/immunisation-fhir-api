import os
import logging
from boto3 import client as boto3_client

logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")

STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", "firehose-name-not-defined")
CONFIG_BUCKET_NAME = os.getenv("CONFIG_BUCKET_NAME", "variconfig-bucketable-not-defined")

REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")

s3_client = boto3_client("s3", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)

# boto_config = Config(region_name=REGION_NAME)
# secretsmanager_client = boto3_client("secretsmanager", config=boto_config)
secrets_manager_client = boto3_client("secretsmanager", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)
