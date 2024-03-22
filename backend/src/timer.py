import logging
import time
import json
from functools import wraps

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")


def log_times_and_info(func):
    """This decorator prints the execution time for the decorated function and logs additional info."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            end = time.time()
            log_info = {
                "time_taken": "{} ran in {}s".format(func.__name__, round(end - start, 5)),
                "function": func.__name__,
                "endpoint": "some_endpoint",
                "correlation_id": "some_correlation_id",
                "request_id": "some_request_id"
            }
            logger.info(json.dumps(log_info))
            return result
        except Exception as e:
            log_error = {
                "error": str(e),
                "function": func.__name__,
                "endpoint": "some_endpoint",
                "correlation_id": "some_correlation_id",
                "request_id": "some_request_id"
            }
            logger.exception(json.dumps(log_error))

    return wrapper