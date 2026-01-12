import logging
import os

from boto3 import client as boto3_client
from boto3 import resource as boto3_resource
from botocore.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", "firehose-name-not-defined")
CONFIG_BUCKET_NAME = os.getenv("CONFIG_BUCKET_NAME", "variconfig-bucketable-not-defined")

REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")

global_s3_client = None
global_sqs_client = None
global_firehose_client = None
global_secrets_manager_client = None
global_dynamodb_client = None
global_dynamodb_resource = None
global_kinesis_client = None


def get_s3_client():
    global global_s3_client
    if global_s3_client is None:
        global_s3_client = boto3_client("s3", region_name=REGION_NAME)
    return global_s3_client


def get_sqs_client():
    global global_sqs_client
    if global_sqs_client is None:
        global_sqs_client = boto3_client("sqs", region_name=REGION_NAME)
    return global_sqs_client


def get_firehose_client():
    global global_firehose_client
    if global_firehose_client is None:
        global_firehose_client = boto3_client("firehose", region_name=REGION_NAME)
    return global_firehose_client


def get_secrets_manager_client():
    global global_secrets_manager_client
    if global_secrets_manager_client is None:
        global_secrets_manager_client = boto3_client("secretsmanager", region_name=REGION_NAME)
    return global_secrets_manager_client


def get_dynamodb_client():
    global global_dynamodb_client
    if global_dynamodb_client is None:
        global_dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)
    return global_dynamodb_client


def get_dynamodb_resource():
    global global_dynamodb_resource
    if global_dynamodb_resource is None:
        global_dynamodb_resource = boto3_resource("dynamodb", region_name=REGION_NAME)
    return global_dynamodb_resource


def get_kinesis_client():
    global global_kinesis_client
    if global_kinesis_client is None:
        global_kinesis_client = boto3_client(
            "kinesis",
            region_name=REGION_NAME,
            config=Config(retries={"mode": "standard"}),
        )
    return global_kinesis_client
