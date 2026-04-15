import json
import os

import boto3

from common.api_clients.constants import MnsNotificationPayload
from common.clients import logger

REGION_NAME = os.getenv("AWS_REGION", "eu-west-2")


class MockMnsService:
    def __init__(self, queue_url):
        self.queue_url = queue_url
        self.sqs_client = boto3.client("sqs", region_name=REGION_NAME)
        logger.info(f"MockMnsService initialized with queue: {queue_url}")

    def publish_notification(self, mns_payload: MnsNotificationPayload) -> None:
        """
        Send MNS notification payload to test SQS queue as fallback.
        Args: payload: MNS notification payload
        """
        try:
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(mns_payload),
                MessageAttributes={"source": {"StringValue": "mns-publisher-lambda", "DataType": "String"}},
            )
            logger.info(
                "Mock MNS: Successfully sent notification to test queue", extra={"message_id": response["MessageId"]}
            )
        except Exception:
            logger.exception("Mock MNS: Failed to send to test SQS queue")
            raise
