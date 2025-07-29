import logging
from mns_setup import get_mns_service


def run_subscription():
    mns = get_mns_service()
    result = mns.check_subscription()
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_subscription()
    logging.info(f"Subscription Result: {result}")
