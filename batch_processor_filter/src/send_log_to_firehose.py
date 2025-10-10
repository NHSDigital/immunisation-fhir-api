import json

import boto3
from constants import REGION_NAME, SPLUNK_FIREHOSE_STREAM_NAME

firehose_client = boto3.client("firehose", region_name=REGION_NAME)


# Not keen on including blocking calls in function code for log data
# Consider simply logging and setting up CW subscription filters to forward to Firehose
# https://docs.aws.amazon.com/firehose/latest/dev/writing-with-cloudwatch-logs.html
def send_log_to_firehose(log_data: dict) -> None:
    """Sends the log_message to Firehose"""
    record = {"Data": json.dumps({"event": log_data}).encode("utf-8")}
    firehose_client.put_record(DeliveryStreamName=SPLUNK_FIREHOSE_STREAM_NAME, Record=record)
