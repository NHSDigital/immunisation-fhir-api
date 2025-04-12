import boto3
import os
import json
from botocore.config import Config

class FirehoseLogger:
    def __init__(
        self,
        boto_client=boto3.client("firehose", config=Config(region_name="eu-west-2")),
        stream_name: str = os.getenv("SPLUNK_FIREHOSE_NAME")
    ):
        self.firehose_client = boto_client
        self.delivery_stream_name = stream_name

    def send_log(self, log_message):
        encoded_log_data = json.dumps(log_message).encode("utf-8")
        s = self.firehose_client.put_record(
            DeliveryStreamName=self.delivery_stream_name,
            Record={"Data": encoded_log_data},
        )
        print(f"Log sent to Firehose: {s}")
