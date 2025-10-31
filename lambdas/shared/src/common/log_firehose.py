import json

from common.clients import firehose_client
from common.clients import logger


def send_log_to_firehose(stream_name: str, log_data: dict) -> None:
    """Sends the log_message to Firehose"""
    try:
        record = {"Data": json.dumps({"event": log_data}).encode("utf-8")}
        response = firehose_client.put_record(DeliveryStreamName=stream_name, Record=record)
        logger.info("Log sent to Firehose: %s", response)
    except Exception as error:  # pylint:disable = broad-exception-caught
        logger.exception("Error sending log to Firehose: %s", error)
