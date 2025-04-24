import boto3
import logging
import json
import os
from botocore.config import Config

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")


class FirehoseLogger:
    def __init__(
        self,
        stream_name: str = os.getenv("SPLUNK_FIREHOSE_NAME"),
        boto_client=boto3.client("firehose", config=Config(region_name="eu-west-2")),
    ):
        self.firehose_client = boto_client
        self.delivery_stream_name = stream_name

    def send_log(self, log_message):
        log_to_splunk = log_message
        encoded_log_data = json.dumps(log_to_splunk).encode("utf-8")
        try:
            response = self.firehose_client.put_record(
                DeliveryStreamName=self.delivery_stream_name,
                Record={"Data": encoded_log_data},
            )
            logger.info(f"Log sent to Firehose: {response}")
        except Exception as e:
            logger.exception(f"Error sending log to Firehose: {e}")
