"""Function to send the message to kinesis"""

import os
import simplejson as json
from botocore.exceptions import ClientError
from clients import kinesis_client, logger


def send_to_kinesis(supplier: str, message_body: dict, vaccine_type: str) -> bool:
    """Send a message to the specified Kinesis stream. Returns a boolean indicating whether the send was successful."""
    stream_name = os.getenv("KINESIS_STREAM_NAME")
    try:
        resp = kinesis_client.put_record(
            StreamName=stream_name,
            StreamARN=os.getenv("KINESIS_STREAM_ARN"),
            Data=json.dumps(message_body, ensure_ascii=False),
            PartitionKey=f"{supplier}_{vaccine_type}",
        )
        logger.info("Message sent to Kinesis stream: %s for supplier: %s with resp: %s", stream_name, supplier, resp)
        return True
    except ClientError as error:
        logger.error("Error sending message to Kinesis: %s", error)
        return False
