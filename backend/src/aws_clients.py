from boto3 import client as boto3_client
import os


REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")

sqs_client = boto3_client("sqs", region_name=REGION_NAME)
