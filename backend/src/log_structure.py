import logging
import boto3
import json
import os
import time
from botocore.config import Config
from functools import wraps

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")


def function_info(func):
    """This decorator prints the execution information for the decorated function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        event = args[0] if args else {}
        headers = event.get("headers", {})
        correlation_id = headers.get("X-Correlation-ID", "X-Correlation-ID not passed")
        request_id = headers.get("X-Request-ID", "X-Request-ID not passed")
        actual_path = event.get("path", "Unknown")
        resource_path = event.get("requestContext", {}).get("resourcePath", "Unknown")
        logger.info(
            f"Starting {func.__name__} with X-Correlation-ID: {correlation_id} and X-Request-ID: {request_id}"
        )

        try:
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            logData = {
                "function_name": func.__name__,
                "time_taken": f"{round(end - start, 5)}s",
                "X-Correlation-ID": correlation_id,
                "X-Request-ID": request_id,
                "actual_path": actual_path,
                "resource_path": resource_path,
                "status": "completed successfully",
            }
            SplunkLogger.log(message = logData)
            logger.info(logData)

            return result

        except Exception as e:
            logData = {
                "function_name": func.__name__,
                "time_taken": f"{round(time.time() - start, 5)}s",
                "X-Correlation-ID": correlation_id,
                "X-Request-ID": request_id,
                "actual_path": actual_path,
                "resource_path": resource_path,
                "error": str(e),
            }
            SplunkLogger.log(message = logData)
            logger.exception(logData)
            raise

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
