import logging
import time
from functools import wraps

logging.basicConfig()
logger = logging.getLogger()


def timed(func):
    """This decorator prints the execution time for the decorated function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        log = {"time_taken": f"{func.__name__} ran in {round(end - start, 5)}s"}
        logger.info(log)
        return result

    return wrapper
