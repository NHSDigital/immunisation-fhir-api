import time
import logging

logging.basicConfig(level="INFO")
logger = logging.getLogger("PERFORMANCE")
logger.setLevel("INFO")

test_marker = {}
std_marker = {}


def dump_stats(marker):
    total = 0

    for name, start_time in marker.items():
        duration = time.perf_counter_ns() - start_time
        elapsed_s = duration / 1_000_000_000
        total += elapsed_s
        logger.info(f"end [{name}]: {elapsed_s:.3f} s")
    logger.info(f"total: {total:.3f} s | average: {total / len(marker):.3f} s")


def monitor(nameMarker, is_test=True):
    t = time.perf_counter_ns()
    marker = test_marker if is_test else std_marker

    if nameMarker in marker:
        duration = t - marker[nameMarker]
        elapsed_ms = duration / 1_000_000
        elapsed_s = elapsed_ms / 1000
        logger.info(f"end [{nameMarker}]: {elapsed_s:.3f} s")
        if is_test:
            dump_stats(marker)
        del marker[nameMarker]  # <-- remove the marker after logging
    else:
        logger.info(f"start [{nameMarker}]")
    marker[nameMarker] = t
