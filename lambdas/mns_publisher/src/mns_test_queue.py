import json
import os

import boto3

from common.clients import logger

MNS_TEST_QUEUE_URL = os.getenv("MNS_TEST_QUEUE_URL")
sqs_client = boto3.client("sqs", region_name="eu-west-2")


def send_notification_to_test_queue(mns_payload: dict) -> None:
    """
    Send MNS notification payload to test SQS queue as fallback.
    Args: payload: MNS notification payload
    """
    if not MNS_TEST_QUEUE_URL:
        logger.error("MNS_TEST_QUEUE_URL environment variable is not set")
        return

    try:
        response = sqs_client.send_message(
            QueueUrl=MNS_TEST_QUEUE_URL,
            MessageBody=json.dumps(mns_payload),
            MessageAttributes={"source": {"StringValue": "mns-publisher-lambda", "DataType": "String"}},
        )
        logger.info("Successfully sent notification to test queue", extra={"message_id": response["MessageId"]})
    except Exception:
        logger.exception("Failed to send to test SQS queue")
