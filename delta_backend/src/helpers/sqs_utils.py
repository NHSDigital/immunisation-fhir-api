import boto3
import json
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()

def send_message(record, queue_url):
    """
    Sends a message to the specified SQS queue.
    """
    # Use boto3 to interact with SQS
    sqs_client = boto3.client("sqs")
    try:
        # Send the record to the queue
        logger.info(f"Sending record to DLQ: {record}")
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(record))
        logger.info("Record saved successfully to the DLQ")
    except ClientError as e:
        logger.error(f"Error sending record to DLQ: {e}")
