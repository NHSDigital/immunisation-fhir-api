import logging
from mns_setup import get_mns_service


def run_unsubscribe():
    mns = get_mns_service()
    result = mns.delete_subscription("0fc9c880-ac76-47c8-99e9-032b894c90b0")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_unsubscribe()
    logging.info(f"Subscription Result: {result}")
