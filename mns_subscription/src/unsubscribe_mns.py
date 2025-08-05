import logging
from mns_setup import get_mns_service


def run_unsubscribe():
    mns = get_mns_service()
    result = mns.delete_subscription("27c13f3b-023d-4a55-a43b-e8b58960a315")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_unsubscribe()
    logging.info(f"Subscription Result: {result}")
