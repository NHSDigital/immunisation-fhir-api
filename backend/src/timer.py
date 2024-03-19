import logging
import time

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
        log = {"time_taken":"{} ran in {}s".format(func.__name__, round(end - start, 5))}
        logger.info(log)
        return result

    return wrapper