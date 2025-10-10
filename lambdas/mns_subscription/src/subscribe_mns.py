import logging

from mns_setup import get_mns_service


def run_subscription():
    mns = get_mns_service()
    return mns.check_subscription()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_subscription()
    logging.info(f"Subscription Result: {result}")
