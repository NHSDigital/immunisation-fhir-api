import time
import logging

logging.basicConfig(level="INFO")
logger = logging.getLogger("PERFORMANCE")
logger.setLevel("INFO")

marker = {}


def monitor(nameMarker):
    t = time.perf_counter_ns()
    if nameMarker in marker:
        duration = t - marker[nameMarker]
        elapsed_ms = duration / 1_000_000
        logger.info(f"end [{nameMarker}]: {elapsed_ms} ms")

        del marker[nameMarker]  # <-- remove the marker after logging
    else:
        logger.info(f"start [{nameMarker}]")
        marker[nameMarker] = t
