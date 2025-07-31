import logging
from mns_setup import get_mns_service


def run_unsubscribe():
    mns = get_mns_service()
    result = mns.check_delete_subscription()
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_unsubscribe()
    logging.debug(f"Subscription Result: {result}")
