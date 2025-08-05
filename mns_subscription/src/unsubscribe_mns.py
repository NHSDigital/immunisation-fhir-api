import logging
from mns_setup import get_mns_service


def run_unsubscribe():
    mns = get_mns_service()
    result = mns.delete_subscription("5914e483-8810-4c4a-b225-19bbdc14d2e7")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_unsubscribe()
    logging.info(f"Subscription Result: {result}")
