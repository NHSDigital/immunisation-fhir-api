import boto3
import logging
import json
import os
import time
from botocore.config import Config
from functools import wraps

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
        log_to_splunk["sourcetype"] = "App_immunisations_dev"
        encoded_log_data = json.dumps(log_to_splunk).encode("utf-8")
        try:
            response = self.firehose_client.put_record(
                DeliveryStreamName=self.delivery_stream_name,
                Record={"Data": encoded_log_data},
            )
            print(f"Log sent to Firehose: {response}")
        except Exception as e:
            print(f"Error sending log to Firehose: {e}")


firehose_logger = FirehoseLogger()


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
            logger.info(result)
            end = time.time()
            outcome = result[0]
            logData = {
                "function_name": func.__name__,
                "time_taken": f"{round(end - start, 5)}s",
                "X-Correlation-ID": correlation_id,
                "X-Request-ID": request_id,
                "actual_path": actual_path,
                "resource_path": resource_path,
                "status": outcome,
                "status_code": "Completed successfully",
            }
            
            firehose_logger.send_log(logData)
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
            firehose_logger.send_log(logData)
            logger.exception(logData)
            raise

    return wrapper
