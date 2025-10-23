"""This module contains the logging decorator for sending the appropriate logs to Cloudwatch and Firehose."""

import json
import os
import time
from datetime import datetime
from functools import wraps

from common.clients import firehose_client, logger

STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", "immunisation-fhir-api-internal-dev-splunk-firehose")


def send_log_to_firehose(log_data: dict) -> None:
    """Sends the log_message to Firehose"""
    try:
        record = {"Data": json.dumps({"event": log_data}).encode("utf-8")}
        response = firehose_client.put_record(DeliveryStreamName=STREAM_NAME, Record=record)
        logger.info("Log sent to Firehose: %s", response)  # TODO: Should we be logging full response?
    except Exception as error:  # pylint:disable = broad-exception-caught
        logger.exception("Error sending log to Firehose: %s", error)


def generate_and_send_logs(
    start_time: float,
    base_log_data: dict,
    additional_log_data: dict,
    use_ms_precision: bool = False,
    is_error_log: bool = False,
) -> None:
    """Generates log data which includes the base_log_data, additional_log_data, and time taken (calculated using the
    current time and given start_time) and sends them to Cloudwatch and Firehose."""
    seconds_elapsed = time.time() - start_time
    formatted_time_elapsed = (
        f"{round(seconds_elapsed * 1000, 5)}ms" if use_ms_precision else f"{round(seconds_elapsed, 5)}s"
    )

    log_data = {
        **base_log_data,
        "time_taken": formatted_time_elapsed,
        **additional_log_data,
    }
    log_function = logger.error if is_error_log else logger.info
    log_function(json.dumps(log_data))
    send_log_to_firehose(log_data)


def logging_decorator(func):
    """
    Sends the appropriate logs to Cloudwatch and Firehose based on the function result.
    NOTE: The function must return a dictionary as its only return value. The dictionary is expected to contain
    all of the required additional details for logging.
    NOTE: Logs will include the result of the function call or, in the case of an Exception being raised,
    a status code of 500 and the error message.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        base_log_data = {
            "function_name": f"filename_processor_{func.__name__}",
            "date_time": str(datetime.now()),
        }
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            generate_and_send_logs(
                start_time,
                base_log_data,
                additional_log_data=result,
                use_ms_precision=True,
            )
            return result

        except Exception as e:
            additional_log_data = {"statusCode": 500, "error": str(e)}
            generate_and_send_logs(
                start_time,
                base_log_data,
                additional_log_data,
                is_error_log=True,
                use_ms_precision=True,
            )
            raise

    return wrapper
