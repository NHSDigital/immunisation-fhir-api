"""Initialise clients, resources and logger. Note that all clients, resources and logger for the E2E BATCH
should be initialised ONCE ONLY (in this file) and then imported into the files where they are needed.
"""

import logging
from constants import (
    environment, REGION,
    batch_fifo_queue_name, ack_metadata_queue_name, audit_table_name
    )
from boto3 import client as boto3_client, resource as boto3_resource


# AWS Clients and Resources


s3_client = boto3_client("s3", region_name=REGION)

dynamodb = boto3_resource("dynamodb", region_name=REGION)
sqs_client = boto3_client('sqs', region_name=REGION)
events_table_name = f"imms-{environment}-imms-events"
events_table = dynamodb.Table(events_table_name)
audit_table = dynamodb.Table(audit_table_name)
batch_fifo_queue_url = sqs_client.get_queue_url(QueueName=batch_fifo_queue_name)['QueueUrl']
ack_metadata_queue_url = sqs_client.get_queue_url(QueueName=ack_metadata_queue_name)['QueueUrl']
# Logger
logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")
