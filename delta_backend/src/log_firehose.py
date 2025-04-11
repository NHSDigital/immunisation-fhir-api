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
        # @SW: SPLUNK_FIREHOSE_NAME doesnt seem to be defined in the Sonorcloud environment
        stream_name: str = os.getenv("SPLUNK_FIREHOSE_NAME", "AAA"),
        boto_client=None,
    ):
        logger.info(">>>>>>FirehoseLogger.init!!!")
        if boto_client is None:
            boto_client = boto3.client("firehose", config=Config(region_name="eu-west-2"))
        self.firehose_client = boto_client
        self.delivery_stream_name = stream_name
        logger.info(f">>>>>> Firehose stream name: {stream_name}")
        # for key, value in os.environ.items():
        #     logger.info(f">>> VAR: {key}: {value}")


    def send_log(self, log_message):
        log_to_splunk = log_message
        logger.info(f"Log sent to Firehose for save: {log_to_splunk}")
        encoded_log_data = json.dumps(log_to_splunk).encode("utf-8")
        try:
            logger.info(f"Send log to Firehose")
            response = self.firehose_client.put_record(
                DeliveryStreamName=self.delivery_stream_name,
                Record={"Data": encoded_log_data},
            )
            logger.info(f"Log sent to Firehose: {response}")
        except Exception as e:
            logger.exception(f"Error sending log to Firehose: {e}")
