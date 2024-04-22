import boto3
import json
import logging
import os
import time
from botocore.config import Config
from functools import wraps

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")


def timed(func):
    """This decorator prints the execution time for the decorated function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        log = {"time_taken": round(end - start, 5), "function_name": func.__name__}
        logger.info(log)
        return result

    return wrapper


class SplunkLogger:
    def __init__(
        self,
        stream_name: str = os.getenv("SPLUNK_FIREHOSE_NAME"),
        boto_client=boto3.client("firehose", config=Config(region_name="eu-west-2")),
    ):
        self.firehose = boto_client
        self.stream_name = stream_name

    def log(self, message: dict):
        """It sends the message to splunk"""
        data = json.dumps(message)

        response = self.firehose.put_record(
            DeliveryStreamName=self.stream_name, Record={"Data": data}
        )
        return response

