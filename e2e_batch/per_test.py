import time
import logging
import json

logging.basicConfig(level="INFO")
logger = logging.getLogger("PERFORMANCE")
logger.setLevel("INFO")

marker = {}


def monitor(nameMarker):  # initialises time for name marker
    t = time.perf_counter_ns()
    if nameMarker in marker:
        marker[nameMarker] = t
    else:
        duration = t - marker[nameMarker]
        elapsed_ms = duration / 1_000_000
        out_msg = {
            "marker": nameMarker,
            "elapsed_time": elapsed_ms
        }
    logger.info(json.dumps(out_msg))
    marker[nameMarker] = t
