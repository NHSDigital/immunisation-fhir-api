from boto3 import client as boto3_client
import os


REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")

s3_client = boto3_client("s3", region_name=REGION_NAME)
kinesis_client = boto3_client("kinesis", region_name=REGION_NAME)
lambda_client = boto3_client("lambda", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
sqs_client = boto3_client("sqs", region_name=REGION_NAME)
