"""This module contains the logging decorator for sending the appropriate logs to Cloudwatch and Firehose.
The decorator log pattern is shared by filenameprocessor, recordprocessor, ack_backend and id_sync modules.
and therefore could be moved to a common module in the future.
TODO: Duplication check has been suppressed in sonar-project.properties. Remove once refactored.
"""

import json
import time
from datetime import datetime
from functools import wraps

from common.clients import logger
from common.log_firehose import send_log_to_firehose


def generate_and_send_logs(
    stream_name: str,
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
    send_log_to_firehose(stream_name, log_data)


def logging_decorator(prefix: str, stream_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info("Starting function: %s", func.__name__)
            base_log_data = {
                "function_name": f"{prefix}_{func.__name__}",
                "date_time": str(datetime.now()),
            }
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                generate_and_send_logs(stream_name, start_time, base_log_data, additional_log_data=result)
                return result
            except Exception as e:
                additional_log_data = {"statusCode": 500, "error": str(e)}
                generate_and_send_logs(
                    stream_name,
                    start_time,
                    base_log_data,
                    additional_log_data,
                    is_error_log=True,
                )
                raise

        return wrapper

    return decorator
