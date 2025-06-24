"""This module contains the logging decorator for sending the appropriate logs to Cloudwatch and Firehose.
    The decorator log pattern is shared by filenameprocessor, recordprocessor, ack_backend and redis_sync modules.
    and therefore could be moved to a common module in the future.
    TODO: refactor to a common module.
"""
import json
import time
from datetime import datetime
from functools import wraps
from clients import firehose_client, logger, STREAM_NAME


def send_log_to_firehose(log_data: dict) -> None:
    """Sends the log_message to Firehose"""
    try:
        record = {"Data": json.dumps({"event": log_data}).encode("utf-8")}
        response = firehose_client.put_record(DeliveryStreamName=STREAM_NAME, Record=record)
        logger.info("Log sent to Firehose: %s", response)
    except Exception as error:  # pylint:disable = broad-exception-caught
        logger.exception("Error sending log to Firehose: %s", error)


def generate_and_send_logs(
    start_time, base_log_data: dict, additional_log_data: dict, is_error_log: bool = False
) -> None:
    """Generates log data which includes the base_log_data, additional_log_data, and time taken (calculated using the
    current time and given start_time) and sends them to Cloudwatch and Firehose."""
    log_data = {**base_log_data, "time_taken": f"{round(time.time() - start_time, 5)}s", **additional_log_data}
    log_function = logger.error if is_error_log else logger.info
    log_function(json.dumps(log_data))
    send_log_to_firehose(log_data)


def logging_decorator(prefix="redis_sync"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            base_log_data = {
                "function_name": f"{prefix}_{func.__name__}",
                "date_time": str(datetime.now())
            }
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                generate_and_send_logs(start_time, base_log_data, additional_log_data=result)
                return result
            except Exception as e:
                additional_log_data = {"statusCode": 500, "error": str(e)}
                generate_and_send_logs(start_time, base_log_data, additional_log_data, is_error_log=True)
                raise
        return wrapper
    return decorator
